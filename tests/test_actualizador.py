# -*- coding: utf-8 -*-
"""Actualizador de yt-dlp sin internet (Fase 7, A2).

Todo se prueba con respuestas de ejemplo y paquetes armados en un directorio
temporal: hash incorrecto, tamaño excesivo, rutas maliciosas, versión igual o
más vieja, host no permitido, prueba de humo fallida, sin internet y límites.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import hashlib
import io
import json
import shutil
import sys
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import actualizador, motor  # noqa: E402

VERSION_NUEVA = "2099.1.1"


def _wheel(version=VERSION_NUEVA, extra=None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("yt_dlp/__init__.py", "from .version import __version__\n")
        z.writestr("yt_dlp/version.py", "__version__ = %r\n" % version)
        for nombre in extra or []:
            z.writestr(nombre, "malicioso")
    return buffer.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.paquete = _wheel()
        self.sha = hashlib.sha256(self.paquete).hexdigest()
        self.estado = motor.ruta_estado()
        self.carpeta = motor.carpeta_motor()
        self.addCleanup(lambda: self.estado.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(self.carpeta, ignore_errors=True))
        self.consultas = []
        actualizador._ya_comprobo = False      # cada test simula un inicio

    def json_pypi(self, version=VERSION_NUEVA, sha=None, tamano=None, url=None):
        return json.dumps({
            "info": {"version": version},
            "urls": [{
                "filename": "yt_dlp--py3-none-any.whl".replace("--", "-%s-" % version),
                "packagetype": "bdist_wheel",
                "size": tamano if tamano is not None else len(self.paquete),
                "digests": {"sha256": sha if sha is not None else self.sha},
                "url": url or "https://files.pythonhosted.org/packages/yt_dlp.whl",
            }],
        }).encode("utf-8")

    def abrir(self, cuerpo=None, github=True, etiqueta=VERSION_NUEVA):
        def _falso(url, tope, tiempo):
            self.consultas.append(url)
            if "api.github.com" in url:
                if not github:
                    raise urllib.error.URLError("sin internet")
                return json.dumps({"tag_name": etiqueta}).encode("utf-8")
            if "pypi.org" in url and "json" in url:
                return cuerpo if cuerpo is not None else self.json_pypi()
            return self.paquete
        return _falso


class CaminoFeliz(Base):
    def test_actualiza_con_hash_y_prueba_ok(self):
        r = actualizador.comprobar(abrir=self.abrir(), probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "actualizada")
        self.assertEqual(r["version"], VERSION_NUEVA)
        self.assertTrue(motor.carpeta_version(VERSION_NUEVA).is_dir())
        self.assertEqual(motor.estado()["activa"], VERSION_NUEVA)
        self.assertEqual(motor.estado()["origen"], "actualizada")

    def test_paquete_extraido_solo_trae_yt_dlp(self):
        actualizador.comprobar(abrir=self.abrir(), probar=lambda c, v: True, forzar=True)
        paquete = motor.carpeta_version(VERSION_NUEVA) / "yt_dlp"
        self.assertTrue((paquete / "__init__.py").is_file())


class VersionNumerica(Base):
    """0.3: las versiones se comparan por números, nunca como texto.

    "2026.10.2" es MÁS NUEVA que "2026.9.30", aunque como texto vaya antes.
    """

    def _comprobar(self, actual, ofrecida):
        motor.guardar_estado(activa=actual, origen="actualizada")
        return actualizador.comprobar(
            abrir=self.abrir(self.json_pypi(version=ofrecida), etiqueta=ofrecida),
            probar=lambda c, v: True, forzar=True)

    def test_octubre_es_mas_nueva_que_septiembre(self):
        self.assertLess("2026.10.2", "2026.9.30")     # como texto, mentira
        self.assertEqual(self._comprobar("2026.9.30", "2026.10.2")["accion"],
                         "actualizada")

    def test_el_cero_delante_no_cambia_la_version(self):
        self.assertEqual(self._comprobar("2026.08.19", "2026.8.19")["accion"],
                         "al_dia")

    def test_parche_mayor_en_el_mismo_mes(self):
        self.assertEqual(self._comprobar("2026.8.19", "2026.9.1")["accion"],
                         "actualizada")


class Rechazos(Base):
    def test_hash_incorrecto(self):
        cuerpo = self.json_pypi(sha="0" * 64)
        r = actualizador.comprobar(abrir=self.abrir(cuerpo), probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "fallo")
        self.assertFalse(motor.carpeta_version(VERSION_NUEVA).exists())

    def test_tamano_excesivo_se_rechaza_antes_de_bajar(self):
        cuerpo = self.json_pypi(tamano=actualizador.TOPE_PAQUETE + 1)
        r = actualizador.comprobar(abrir=self.abrir(cuerpo), probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "fallo")
        self.assertFalse(any("files.pythonhosted" in u for u in self.consultas))

    def test_version_igual_o_mas_vieja_se_ignora(self):
        for vieja in (motor.version_en_uso(), "2000.1.1"):
            self.consultas.clear()
            r = actualizador.comprobar(abrir=self.abrir(self.json_pypi(version=vieja)),
                                       probar=lambda c, v: True, forzar=True)
            self.assertEqual(r["accion"], "al_dia")
            self.assertFalse(any("files.pythonhosted" in u for u in self.consultas))

    def test_version_mala_conocida_no_se_reintenta(self):
        motor.guardar_estado(malas=[VERSION_NUEVA])
        r = actualizador.comprobar(abrir=self.abrir(), probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "al_dia")
        self.assertFalse(any("files.pythonhosted" in u for u in self.consultas))

    def test_sin_lanzamiento_oficial_no_se_activa(self):
        r = actualizador.comprobar(abrir=self.abrir(github=False),
                                   probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "fallo")
        self.assertIsNone(motor.estado()["activa"])

    def test_etiqueta_de_github_distinta_no_se_activa(self):
        r = actualizador.comprobar(abrir=self.abrir(etiqueta="2098.1.1"),
                                   probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "fallo")
        self.assertIsNone(motor.estado()["activa"])

    def test_la_etiqueta_se_compara_por_numeros(self):
        # PyPI: 2026.8.19 / GitHub: 2026.08.19 (misma versión)
        r = actualizador.comprobar(abrir=self.abrir(etiqueta="2099.01.01"),
                                   probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "actualizada")

    def test_prueba_de_humo_fallida_descarta_y_marca(self):
        r = actualizador.comprobar(abrir=self.abrir(), probar=lambda c, v: False, forzar=True)
        self.assertEqual(r["accion"], "al_dia")
        self.assertIn(VERSION_NUEVA, motor.estado()["malas"])
        self.assertFalse(motor.carpeta_version(VERSION_NUEVA).exists())
        # y no queda ninguna carpeta temporal tirada
        self.assertEqual(list(motor.carpeta_motor().glob("tmp-*")), [])

    def test_sin_internet_es_silencio(self):
        def _sin_red(url, tope, tiempo):
            raise urllib.error.URLError("sin internet")
        r = actualizador.comprobar(abrir=_sin_red, probar=lambda c, v: True, forzar=True)
        self.assertEqual(r["accion"], "fallo")
        self.assertIsNone(motor.estado()["activa"])


class Limites(Base):
    def test_una_comprobacion_por_inicio(self):
        llamadas = []
        with mock.patch.object(actualizador, "comprobar",
                               lambda **k: llamadas.append(1) or {"accion": "al_dia"}):
            hilo1 = actualizador.comprobar_en_segundo_plano()
            hilo2 = actualizador.comprobar_en_segundo_plano()
        if hilo1:
            hilo1.join(5)
        self.assertIsNone(hilo2)
        self.assertEqual(len(llamadas), 1)

    def test_menos_de_diez_minutos_se_omite(self):
        motor.guardar_estado(ultima_comprobacion=motor.ahora())
        r = actualizador.comprobar(abrir=self.abrir(), probar=lambda c, v: True)
        self.assertEqual(r["accion"], "omitida")
        self.assertEqual(self.consultas, [])

    def test_forzar_salta_el_limite_de_tiempo(self):
        motor.guardar_estado(ultima_comprobacion=motor.ahora())
        r = actualizador.comprobar(abrir=self.abrir(), probar=lambda c, v: True, forzar=True)
        self.assertNotEqual(r["accion"], "omitida")

    def test_interruptor_apagado_no_comprueba(self):
        from miauki.core import settings
        settings.cambiar("actualizar_motor_auto", False)
        self.addCleanup(settings.cambiar, "actualizar_motor_auto", True)
        self.consultas.clear()
        hilo = actualizador.comprobar_en_segundo_plano()
        self.assertIsNone(hilo)
        self.assertEqual(self.consultas, [])

    def test_el_motor_en_uso_no_cambia_con_descarga_en_curso(self):
        """Importar una versión nueva no altera el módulo ya cargado (sesión)."""
        modulo = motor.ytdlp()
        actualizador.comprobar(abrir=self.abrir(), probar=lambda c, v: True, forzar=True)
        self.assertIs(motor.ytdlp(), modulo)
        self.assertEqual(motor.version_en_uso(), modulo.version.__version__)


class Red(Base):
    def test_host_no_permitido_tras_redireccion(self):
        class Respuesta:
            headers = {}

            def geturl(self):
                return "https://sitio-raro.example/yt_dlp.whl"

            def read(self, n=-1):
                return b""

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        with mock.patch("urllib.request.urlopen", return_value=Respuesta()):
            with self.assertRaises(actualizador.Falla):
                actualizador._abrir("https://pypi.org/pypi/yt-dlp/json", 10, 1)

    def test_respuesta_mas_grande_que_el_tope(self):
        class Respuesta:
            headers = {"Content-Length": "999999999"}

            def geturl(self):
                return "https://pypi.org/pypi/yt-dlp/json"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        with mock.patch("urllib.request.urlopen", return_value=Respuesta()):
            with self.assertRaises(actualizador.Falla):
                actualizador._abrir("https://pypi.org/pypi/yt-dlp/json", 100, 1)


class RutasMaliciosas(Base):
    def test_zip_slip_se_ignora(self):
        paquete = _wheel(extra=["../evil.txt", "/absoluto.txt",
                                "yt_dlp/../../otro.txt", "otra_carpeta/x.py"])
        destino = motor.carpeta_motor() / "prueba"
        destino.mkdir(parents=True)
        actualizador._extraer(paquete, destino)
        self.assertTrue((destino / "yt_dlp" / "__init__.py").is_file())
        self.assertFalse((destino.parent / "evil.txt").exists())
        self.assertFalse((destino / "otra_carpeta").exists())
        self.assertFalse((destino.parent.parent / "otro.txt").exists())


if __name__ == "__main__":
    unittest.main()

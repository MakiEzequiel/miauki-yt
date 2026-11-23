# -*- coding: utf-8 -*-
"""Tests de validacion.py (Fase 4 Parte 0, P0.7).

El borde trata todo lo que llega de la interfaz como hostil: snapshot del
encolado, rutas y elección de carpeta.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import validacion  # noqa: E402
from miauki.core.errors import ErrorMiauki  # noqa: E402

BUENO = {
    "url_canonica": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "tipo": "video",
    "selector": "137+140",
    "contenedor": "mp4",
    "kbps": None,
    "titulo": "Me at the zoo",
    "miniatura": "data:image/png;base64,AAA",
    "con_subs": True,
}


class Snapshot(unittest.TestCase):
    def test_snapshot_bueno_pasa(self):
        limpio = validacion.snapshot_limpio(dict(BUENO))
        self.assertEqual(limpio["url_canonica"], BUENO["url_canonica"])
        self.assertEqual(limpio["selector"], "137+140")

    def test_claves_desconocidas_se_descartan(self):
        # La interfaz no puede colar opciones de yt-dlp ni rutas de salida.
        limpio = validacion.snapshot_limpio(dict(
            BUENO, outtmpl="C:\\Windows\\evil.%(ext)s", format="evil",
            rutas="\\\\servidor\\share"))
        for prohibida in ("outtmpl", "format", "rutas"):
            self.assertNotIn(prohibida, limpio)

    def test_selector_con_caracteres_raros_se_rechaza(self):
        for malo in ("137; del *", "137|140", "$(x)", "a b", ""):
            with self.assertRaises(ErrorMiauki, msg=malo):
                validacion.snapshot_limpio(dict(BUENO, selector=malo))

    def test_selector_por_altura_de_ytdlp_se_acepta(self):
        # P0.5: los selectores por altura+códec con respaldos son válidos.
        bueno = ("bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]"
                 "/best[height<=1080][ext=mp4]/best")
        limpio = validacion.snapshot_limpio(dict(BUENO, selector=bueno))
        self.assertEqual(limpio["selector"], bueno)

    def test_resolucion_se_valida(self):
        self.assertIsNone(validacion.snapshot_limpio(dict(BUENO))["resolucion"])
        self.assertEqual(
            validacion.snapshot_limpio(dict(BUENO, resolucion=1080))["resolucion"],
            1080)
        for malo in ("1080", 0, -1, 1.5, True):
            with self.assertRaises(ErrorMiauki, msg=repr(malo)):
                validacion.snapshot_limpio(dict(BUENO, resolucion=malo))

    def test_kbps_fuera_de_lista_se_rechaza(self):
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, kbps=192))

    def test_contenedor_fuera_de_lista_se_rechaza(self):
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, contenedor="avi"))

    def test_esquema_no_http_se_rechaza(self):
        for malo in ("javascript:alert(1)", "file:///C:/x",
                     "ftp://x/y"):
            with self.assertRaises(ErrorMiauki, msg=malo):
                validacion.snapshot_limpio(dict(BUENO, url_canonica=malo))

    def test_miniatura_que_no_es_imagen_se_rechaza(self):
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, miniatura="javascript:x"))

    def test_miniatura_gigante_se_rechaza(self):
        grande = "data:image/png;base64," + "A" * 3_000_100
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, miniatura=grande))

    def test_imagen_con_selector_se_rechaza(self):
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, tipo="imagen"))

    def test_titulo_muy_largo_se_rechaza(self):
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, titulo="x" * 501))


class Playlist(unittest.TestCase):
    """Paso 3 del plan de playlists: entradas validadas una por una."""

    def test_playlist_de_dos_entradas_pasa(self):
        e1 = dict(BUENO, titulo="Video 1")
        e2 = dict(BUENO, titulo="Video 2", con_subs=False)
        limpio = validacion.snapshot_limpio(dict(BUENO, entradas=[e1, e2]))
        self.assertEqual(len(limpio["entradas"]), 2)
        self.assertEqual(limpio["entradas"][0]["titulo"], "Video 1")
        # Cada entrada es un snapshot completo y limpio por sí misma.
        self.assertEqual(limpio["entradas"][1]["url_canonica"],
                         BUENO["url_canonica"])

    def test_snapshot_sin_entradas_no_trae_la_clave(self):
        limpio = validacion.snapshot_limpio(dict(BUENO))
        self.assertNotIn("entradas", limpio)

    def test_entrada_mala_se_rechaza(self):
        e = dict(BUENO, selector="FORMATO MALO")
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, entradas=[e]))

    def test_entradas_no_dict_se_rechazan(self):
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, entradas=["x"]))
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, entradas=None))

    def test_playlist_vacia_se_rechaza(self):
        with self.assertRaises(ErrorMiauki):
            validacion.snapshot_limpio(dict(BUENO, entradas=[]))

    def test_playlist_muy_larga_se_rechaza(self):
        muchas = [dict(BUENO, titulo=f"v{i}") for i in range(601)]
        with self.assertRaises(ErrorMiauki) as ctx:
            validacion.snapshot_limpio(dict(BUENO, entradas=muchas))
        self.assertEqual(ctx.exception.codigo, "playlist_muy_larga")

    def test_playlist_de_600_pasa(self):
        seiscientos = [dict(BUENO, titulo=f"v{i}") for i in range(600)]
        limpio = validacion.snapshot_limpio(dict(BUENO, entradas=seiscientos))
        self.assertEqual(len(limpio["entradas"]), 600)


class NormalizarUrl(unittest.TestCase):
    """Plan `plan.md`, paso 3.5: la normalización es una sola (la de sites)."""

    def test_www(self):
        self.assertEqual(validacion.normalizar_url("www.instagram.com/maki/"),
                         "https://www.instagram.com/maki/")

    def test_dominio_con_ruta(self):
        self.assertEqual(validacion.normalizar_url("minombre.io/video"),
                         "https://minombre.io/video")

    def test_lo_que_no_es_link(self):
        for texto in ["hola", "", "   ", "hola.com", "ftp://x.com/a", None]:
            self.assertIsNone(validacion.normalizar_url(texto), repr(texto))

    def test_respeta_http(self):
        self.assertEqual(validacion.normalizar_url("http://youtu.be/abc"),
                         "http://youtu.be/abc")


class SitioDelSnapshot(unittest.TestCase):
    """Fase 7, 0.2: el sitio sale del link, no de la interfaz."""

    def test_sitio_sale_del_link(self):
        for url, sitio in (
            ("https://www.youtube.com/watch?v=jNQXAC9IVRw", "youtube"),
            ("https://www.tiktok.com/@a/video/123", "tiktok"),
            ("https://www.instagram.com/reel/abc/", "instagram"),
            ("https://www.facebook.com/reel/123", "facebook"),
            ("https://x.com/alguien/status/123", "x"),
            ("https://ejemplo.com/video/1", "otro"),
        ):
            limpio = validacion.snapshot_limpio(dict(BUENO, url_canonica=url))
            self.assertEqual(limpio["sitio"], sitio, url)

    def test_lo_que_diga_la_interfaz_se_ignora(self):
        limpio = validacion.snapshot_limpio(dict(BUENO, sitio="otro"))
        self.assertEqual(limpio["sitio"], "youtube")


class Rutas(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        (self.base / "sub").mkdir()

    def test_dentro_de_acepta_subcarpeta(self):
        self.assertTrue(validacion.dentro_de(str(self.base / "sub"), str(self.base)))

    def test_dentro_de_rechaza_escape_con_puntos(self):
        afuera = os.path.join(str(self.base), "..", "afuera")
        self.assertFalse(validacion.dentro_de(afuera, str(self.base)))

    def test_dentro_de_rechaza_carpeta_hermana(self):
        self.assertFalse(validacion.dentro_de(str(self.base.parent), str(self.base)))

    def test_carpeta_peligrosa(self):
        self.assertTrue(validacion.carpeta_peligrosa("C:\\"))
        self.assertTrue(validacion.carpeta_peligrosa("C:\\Windows"))
        self.assertTrue(validacion.carpeta_peligrosa(r"C:\Program Files\App"))
        self.assertFalse(validacion.carpeta_peligrosa(str(self.base)))

    def test_puede_escribir(self):
        self.assertTrue(validacion.puede_escribir(str(self.base)))

    def test_puede_escribir_ruta_inexistente(self):
        self.assertFalse(validacion.puede_escribir(str(self.base / "no-existe")))


class Nombres(unittest.TestCase):
    """P0.6c: saneado de nombres de Windows y largo total de la ruta."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)

    def test_quita_caracteres_ilegales(self):
        self.assertEqual(validacion.sanear_nombre('a\\b/c:d*e?f"g<h>i|j'),
                         "abcdefghij")

    def test_saca_punto_y_espacio_final(self):
        self.assertEqual(validacion.sanear_nombre("  hola.  "), "hola")
        self.assertEqual(validacion.sanear_nombre("punto.final."), "punto.final")

    def test_nombres_reservados_se_despegan(self):
        self.assertEqual(validacion.sanear_nombre("CON"), "CON_")
        self.assertEqual(validacion.sanear_nombre("con.txt"), "con_.txt")
        self.assertEqual(validacion.sanear_nombre("NUL"), "NUL_")
        self.assertEqual(validacion.sanear_nombre("COM1"), "COM1_")

    def test_vacio_si_no_queda_nada(self):
        self.assertEqual(validacion.sanear_nombre("   ...   "), "")

    def test_base_libre_usa_el_titulo(self):
        self.assertEqual(
            validacion.nombre_base_libre(str(self.base), "Me at the zoo"),
            "Me at the zoo")

    def test_base_libre_agrega_2_y_3(self):
        (self.base / "Me at the zoo.mp4").write_bytes(b"x")
        self.assertEqual(
            validacion.nombre_base_libre(str(self.base), "Me at the zoo"),
            "Me at the zoo (2)")
        (self.base / "Me at the zoo (2).mkv").write_bytes(b"x")
        self.assertEqual(
            validacion.nombre_base_libre(str(self.base), "Me at the zoo"),
            "Me at the zoo (3)")

    def test_base_libre_cuenta_subtitulos_y_otras_extensiones(self):
        (self.base / "foto.jpg").write_bytes(b"x")
        (self.base / "foto.es.srt").write_bytes(b"x")
        self.assertEqual(validacion.nombre_base_libre(str(self.base), "foto"),
                         "foto (2)")

    def test_base_libre_recorta_por_el_largo_total(self):
        largo = "x" * 400
        base = validacion.nombre_base_libre(str(self.base), largo)
        self.assertLessEqual(len(os.path.abspath(
            os.path.join(self.base, base))), validacion.MAX_RUTA)

    def test_base_libre_sin_carpeta_no_falla(self):
        base = validacion.nombre_base_libre("no-existe-jamas", "hola")
        self.assertEqual(base, "hola")

    def test_base_libre_ignora_temporales_de_ytdlp(self):
        # ajustes 21/11: un .part o un fragmento NO ocupa el nombre → se
        # reutiliza la misma base al reanudar (no "X (2)").
        (self.base / "Me at the zoo.mp4.part").write_bytes(b"x")
        self.assertEqual(
            validacion.nombre_base_libre(str(self.base), "Me at the zoo"),
            "Me at the zoo")
        (self.base / "Me at the zoo.f137.mp4").write_bytes(b"x")
        self.assertEqual(
            validacion.nombre_base_libre(str(self.base), "Me at the zoo"),
            "Me at the zoo")
        (self.base / "Me at the zoo.ytdl").write_bytes(b"x")
        self.assertEqual(
            validacion.nombre_base_libre(str(self.base), "Me at the zoo"),
            "Me at the zoo")

    def test_base_libre_temporales_no_ocultan_el_archivo_real(self):
        # Si ya existe el archivo final, el temporal no lo enmascara: igual se
        # elige "X (2)" (nunca se pisa un archivo real).
        (self.base / "foto.mp4").write_bytes(b"x")
        (self.base / "foto.mp4.part").write_bytes(b"x")
        self.assertEqual(validacion.nombre_base_libre(str(self.base), "foto"),
                         "foto (2)")


if __name__ == "__main__":
    unittest.main()

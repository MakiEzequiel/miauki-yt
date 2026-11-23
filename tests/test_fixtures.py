# -*- coding: utf-8 -*-
"""B8: tests con fixtures de las corridas REALES de B9 (spec §5).

Las fixtures salen de tools/probar_links.py (A2): respuestas crudas de
yt-dlp del 15/10/2026, limpiadas a mano (sin URLs firmadas, IDs de usuario,
cabeceras ni tokens) y revisadas antes del commit. No tocan la red.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import json
import sys
import unicodedata as ud
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import analyzer, errors, sites  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _resultado(nombre: str) -> dict:
    info = json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))
    url = info["webpage_url"]
    sitio, _ = sites.detectar(url)
    with mock.patch("miauki.core.images.data_uri_de", return_value=None):
        return analyzer._resultado_de(info, sitio, url)


class YoutubeReal(unittest.TestCase):
    """B9 link 2: Jósean Log - Doma (Lyric Video)."""

    @classmethod
    def setUpClass(cls):
        cls.r = _resultado("youtube_pCPYb7KPoUc.json")

    def test_datos_reales(self):
        self.assertEqual(self.r["tipo"], "video")
        self.assertEqual(self.r["sitio"], "youtube")
        # El sitio devuelve el acento combinante (NFD): comparamos en NFC.
        self.assertEqual(ud.normalize("NFC", self.r["titulo"]),
                         "Jósean Log - Doma (Lyric Video)")
        self.assertEqual(ud.normalize("NFC", self.r["autor"]), "Jósean Log")
        self.assertEqual(self.r["duracion"], 189)

    def test_tipos_y_calidades_reales(self):
        self.assertEqual(self.r["tipos"], ["video", "musica", "imagen"])
        self.assertEqual(
            [(c["etiqueta"], c["recomendada"]) for c in self.r["calidades"]],
            [("1080p", "La mejor"), ("480p", "Equilibrada"),
             ("720p", None), ("360p", None), ("240p", None), ("144p", None)])
        # Política mp4 (Fase 3B): a cada resolución existe H.264+AAC real,
        # así que las tres opciones son mp4 con audio 140 (m4a).
        c = {x["etiqueta"]: x for x in self.r["calidades"]}
        self.assertIn("height<=1080", c["1080p"]["selector"])
        self.assertIn("vcodec^=avc1", c["1080p"]["selector"])
        self.assertEqual(c["1080p"]["contenedor"], "mp4")
        self.assertEqual(c["720p"]["contenedor"], "mp4")
        self.assertEqual(c["480p"]["contenedor"], "mp4")

    def test_subs_automaticos_con_advertencia(self):
        subs = self.r["subtitulos"]
        self.assertTrue(subs["disponible"])
        self.assertEqual(subs["idiomas"][:4], ["es", "en", "aa", "ab"])
        self.assertIn("Los subtítulos son automáticos: pueden tener errores.",
                      self.r["advertencias"])

    def test_musica_tres_y_sin_miniatura_en_la_fixture(self):
        # La fixture no trae thumbnail (limpieza A2): imagenes queda vacío.
        self.assertEqual(len(self.r["musica"]), 1)
        self.assertEqual(self.r["imagenes"], [])
        self.assertIsNone(self.r["miniatura"])


class InstagramReal(unittest.TestCase):
    """B9 link 3: reel de Mundo en Conflicto."""

    @classmethod
    def setUpClass(cls):
        cls.r = _resultado("instagram_Def341BAmx8.json")

    def test_datos_reales(self):
        self.assertEqual(self.r["tipo"], "video")
        self.assertEqual(self.r["sitio"], "instagram")
        self.assertEqual(self.r["titulo"], "Video by mundoeconflictonet")
        self.assertEqual(self.r["autor"], "Mundo en Conflicto")
        self.assertIsNone(self.r["duracion"])

    def test_sin_subs_ni_advertencias(self):
        self.assertFalse(self.r["subtitulos"]["disponible"])
        self.assertEqual(self.r["subtitulos"]["idiomas"], [])
        self.assertEqual(self.r["advertencias"], [])

    def test_calidades_reales(self):
        # Es un reel vertical (1080×1920): la decisión de Maki (15/10/2026)
        # etiqueta por el lado corto → "1080p", no "1920p".
        # Nueva regla (08/11): recomendadas = [min(max,8K), 1080, 480] con dedupe.
        # max=1080 → [1080, 1080, 480] → 1080p "La mejor".
        # No hay formato con lado_corto <= 480 → solo "La mejor" como recomendada.
        # La fixture tiene 1080p, 720p, 540p (lado corto).
        self.assertEqual(
            [(c["etiqueta"], c["recomendada"]) for c in self.r["calidades"]],
            [("1080p", "La mejor"), ("720p", None), ("540p", None)])


class FacebookReal(unittest.TestCase):
    """B9 link 4: video de Anatomía Universal en Facebook."""

    @classmethod
    def setUpClass(cls):
        cls.r = _resultado("facebook_watch_1031839366337796.json")

    def test_datos_reales(self):
        self.assertEqual(self.r["tipo"], "video")
        self.assertEqual(self.r["sitio"], "facebook")
        self.assertEqual(
            self.r["titulo"],
            "2.1M views · 43K reactions | 5 Alimentos que ayudan a "
            "desinflamar el Hígado #anatomia #higado #Higadograso #anatomy "
            "#medicina #medicine #salud #alimentos #VidaSana | "
            "Anatomía Universal")
        self.assertEqual(self.r["autor"], "Anatomía Universal")
        self.assertEqual(self.r["duracion"], 37)

    def test_calidades_reales(self):
        # Reel vertical: lado corto 1080 (decisión 15/10/2026).
        # Nueva regla (08/11): recomendadas = [min(max,8K), 1080, 480] con dedupe.
        # max=1080 → [1080, 1080, 480] → 1080p "La mejor".
        # No hay formato con lado_corto <= 480 → solo "La mejor" como recomendada.
        # La fixture tiene 1080p, 720p (lado corto).
        self.assertEqual(
            [(c["etiqueta"], c["recomendada"]) for c in self.r["calidades"]],
            [("1080p", "La mejor"), ("720p", None)])

    def test_sin_subs(self):
        self.assertFalse(self.r["subtitulos"]["disponible"])
        self.assertEqual(self.r["advertencias"], [])


class ErroresRealesB9(unittest.TestCase):
    """Mensajes reales capturados en la corrida de B9 (links 5 y 6)."""

    def test_twitter_imagen_no_es_video(self):
        self.assertEqual(
            errors.codigo_de(
                "ERROR: [twitter] 2110183275461513256: Media #1 is not a video"),
            "no_es_video")

    def test_foto_de_facebook_no_soportada(self):
        self.assertEqual(
            errors.codigo_de(
                "ERROR: Unsupported URL: "
                "https://www.facebook.com/photo/?fbid=1111696508036243"),
            "sitio_no_soportado")


class LimpiezaA2(unittest.TestCase):
    """Ninguna fixture puede tener datos sensibles (A2)."""

    def test_fixture_sin_urls_firmadas_ni_ids(self):
        marcas = ("googlevideo", "http_headers", "manifest_url",
                  "uploader_id", "\"url\":", "oh=", "oe=", "sig=",
                  "pot=", "thumbnail")
        rutas = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(rutas), 3)
        for ruta in rutas:
            texto = ruta.read_text(encoding="utf-8")
            json.loads(texto)  # además: que sea JSON válido
            for marca in marcas:
                self.assertNotIn(
                    marca, texto,
                    f"{ruta.name}: quedó la marca {marca}")


class ContratoParaLaInterfaz(unittest.TestCase):
    """Fase 3B: cada fixture debe traer TODO lo que app.js lee en la UI."""

    CAMPOS = ("id_solicitud", "tipo", "sitio", "titulo", "autor", "duracion",
              "miniatura", "url_canonica", "tipos", "subtitulos", "calidades",
              "musica", "imagenes", "imagenes_urls", "advertencias")

    @classmethod
    def setUpClass(cls):
        cls.resultados = [
            _resultado("youtube_pCPYb7KPoUc.json"),
            _resultado("instagram_Def341BAmx8.json"),
            _resultado("facebook_watch_1031839366337796.json"),
        ]

    def test_campos_del_contrato(self):
        for r in self.resultados:
            for campo in self.CAMPOS:
                with self.subTest(fixture=r["sitio"], campo=campo):
                    self.assertIn(campo, r)

    def test_subtitulos_tiene_disponible_e_idiomas(self):
        for r in self.resultados:
            subs = r["subtitulos"]
            with self.subTest(sitio=r["sitio"]):
                self.assertIsInstance(subs["disponible"], bool)
                self.assertIsInstance(subs["idiomas"], list)

    def test_cada_calidad_trae_lo_que_la_ui_pinta(self):
        for r in self.resultados:
            for c in r["calidades"]:
                with self.subTest(sitio=r["sitio"], etiqueta=c["etiqueta"]):
                    self.assertIsInstance(c["resolucion"], (int, float))
                    self.assertIn(c["recomendada"],
                                  (None, "La mejor", "Equilibrada", "Liviana"))
                    self.assertTrue(c["selector"])
                    self.assertTrue(c["contenedor"])

    def test_cada_opcion_de_musica_trae_kbps(self):
        for r in self.resultados:
            for m in r["musica"]:
                with self.subTest(sitio=r["sitio"], kbps=m["kbps"]):
                    self.assertEqual(m["kbps"], 320)
                    self.assertIn("peso_bytes", m)
                    self.assertIn("peso_aprox", m)

    def test_miniatura_e_imagenes_solo_data_uri_o_none(self):
        for r in self.resultados:
            with self.subTest(sitio=r["sitio"]):
                for uri in [r["miniatura"]] + list(r["imagenes"]):
                    if uri is not None:
                        self.assertTrue(uri.startswith("data:image/"))

    def test_imagenes_urls_solo_http(self):
        # Las URLs reales (para encolar, 3d.13) nunca son data:.
        for r in self.resultados:
            with self.subTest(sitio=r["sitio"]):
                for u in r["imagenes_urls"]:
                    self.assertTrue(u.startswith("http"))


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Demo de calidades (Fase 2D.2 §5): reglas de DECISIONES.md §5b."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core.formats import calidades_recomendadas, contenedor_de  # noqa: E402


class Calidades(unittest.TestCase):
    def test_4k_completo(self):
        self.assertEqual(calidades_recomendadas(2160), ["2160p", "1080p", "480p"])

    def test_8k_no_se_pasa_de_8k(self):
        self.assertEqual(calidades_recomendadas(4320), ["4320p", "1080p", "480p"])

    def test_1440_activa_equilibrada_1080(self):
        self.assertEqual(calidades_recomendadas(1440), ["1440p", "1080p", "480p"])

    def test_900_equilibrada_baja_a_720(self):
        # altura real no estándar: Mejor etiqueta el 900p real, Equilibrada=1080, Liviana=480
        self.assertEqual(calidades_recomendadas(900), ["900p", "1080p", "480p"])

    def test_720(self):
        self.assertEqual(calidades_recomendadas(720), ["720p", "1080p", "480p"])

    def test_480_liviana_coincide_con_mejor(self):
        # dedupe: Mejor=480 y 480 propuesto -> 480 aparece una vez
        self.assertEqual(calidades_recomendadas(480), ["480p", "1080p"])

    def test_360_sin_equilibrada_ni_liviana(self):
        # etiquetas puras internas: 360p (Mejor), 1080p (Equilibrada), 480p (Liviana)
        # el fallback visible lo resuelve _calidades()
        self.assertEqual(calidades_recomendadas(360), ["360p", "1080p", "480p"])

    def test_sin_dato_no_inventa(self):
        self.assertEqual(calidades_recomendadas(0), [])
        self.assertEqual(calidades_recomendadas(None), [])


class Contenedor(unittest.TestCase):
    """Regla de la spec §4: mp4 si los códecs son compatibles, si no mkv."""

    def test_h264_mas_aac_es_mp4(self):
        self.assertEqual(contenedor_de("avc1.640028", "mp4a.40.2"), "mp4")

    def test_h264_solo_video_es_mp4(self):
        self.assertEqual(contenedor_de("avc1.64001f", "none"), "mp4")

    def test_vp9_da_mkv(self):
        self.assertEqual(contenedor_de("vp09.00.10.08", "opus"), "mkv")

    def test_av1_da_mkv(self):
        self.assertEqual(contenedor_de("av01.0.08M.08", "mp4a.40.2"), "mkv")

    def test_h264_con_opus_da_mkv(self):
        self.assertEqual(contenedor_de("avc1.4d401f", "opus"), "mkv")

    def test_sin_video_con_aac_es_mp4(self):
        self.assertEqual(contenedor_de("none", "mp4a.40.2"), "mp4")

    def test_sin_video_con_opus_da_mkv(self):
        self.assertEqual(contenedor_de("none", "opus"), "mkv")


if __name__ == "__main__":
    unittest.main()

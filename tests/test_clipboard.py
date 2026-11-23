# -*- coding: utf-8 -*-
"""Tests de clipboard.py: detección del link en el texto del portapapeles."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import ctypes
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import clipboard  # noqa: E402


class LinkEnTexto(unittest.TestCase):
    def test_link_solo(self):
        self.assertEqual(clipboard.link_en_texto("https://youtu.be/abc"),
                         "https://youtu.be/abc")

    def test_link_dentro_de_una_frase(self):
        self.assertEqual(
            clipboard.link_en_texto("mirá esto: https://x.com/u/status/123 listo"),
            "https://x.com/u/status/123")

    def test_saca_puntuacion_final(self):
        self.assertEqual(clipboard.link_en_texto("https://youtu.be/abc."),
                         "https://youtu.be/abc")
        self.assertEqual(clipboard.link_en_texto("https://youtu.be/abc,"),
                         "https://youtu.be/abc")

    def test_saca_parentesis_y_comillas(self):
        self.assertEqual(clipboard.link_en_texto('(https://youtu.be/abc)'),
                         "https://youtu.be/abc")
        self.assertEqual(clipboard.link_en_texto('"https://youtu.be/abc"'),
                         "https://youtu.be/abc")

    def test_esquema_en_mayusculas(self):
        self.assertEqual(clipboard.link_en_texto("HTTPS://youtu.be/abc"),
                         "HTTPS://youtu.be/abc")

    def test_sin_link(self):
        for texto in ["hola", "", "   ", "ftp://x.com/a", None, 123,
                      b"https://x.com"]:
            self.assertIsNone(clipboard.link_en_texto(texto), repr(texto))

    def test_www_dominio(self):
        """Plan `plan.md`, paso 3.1: `www.` sin esquema se acepta."""
        self.assertEqual(clipboard.link_en_texto("mira www.instagram.com/maki/"),
                         "https://www.instagram.com/maki/")

    def test_dominio_desnudo_con_path(self):
        self.assertEqual(clipboard.link_en_texto("mira minombre.io/video123"),
                         "https://minombre.io/video123")

    def test_dominio_desnudo_sin_path_NO(self):
        self.assertIsNone(clipboard.link_en_texto("visita minombre.io porfa"))

    def test_http_tambien(self):
        self.assertEqual(clipboard.link_en_texto("http://youtu.be/abc"),
                         "http://youtu.be/abc")

    def test_https_prependido(self):
        self.assertEqual(clipboard.link_en_texto("www.youtube.com/watch?v=x"),
                         "https://www.youtube.com/watch?v=x")

    def test_gana_el_primero(self):
        self.assertEqual(
            clipboard.link_en_texto("https://a.com/1 y https://b.com/2"),
            "https://a.com/1")

    def test_tope_de_largo(self):
        largo = "https://a.com/" + "x" * 2100
        self.assertIsNone(clipboard.link_en_texto(largo))
        justo = "https://a.com/" + "x" * (2048 - 14)
        self.assertEqual(len(clipboard.link_en_texto(justo)), 2048)


class PortapapelesReal(unittest.TestCase):
    def test_no_rompe_y_devuelve_texto_o_none(self):
        # Toca el portapapeles real (solo lectura) y nunca lanza.
        resultado = clipboard.link_del_portapapeles()
        self.assertTrue(resultado is None or isinstance(resultado, str))


class LecturaAcotada(unittest.TestCase):
    """El bug del soak del 20/10: pedir 64 K sobre un bloque chico = AV."""

    def _falsos(self, tamaño):
        u, k = mock.MagicMock(), mock.MagicMock()
        u.OpenClipboard.return_value = 1
        u.IsClipboardFormatAvailable.return_value = 1
        u.GetClipboardData.return_value = 0x1234
        k.GlobalLock.return_value = 0x5678
        k.GlobalSize.return_value = tamaño
        falso = mock.MagicMock()
        falso.user32, falso.kernel32 = u, k
        return falso

    def test_lee_solo_lo_que_entra_en_el_bloque(self):
        falso = self._falsos(24)          # 12 caracteres, texto de 4 + NUL
        with mock.patch.object(ctypes, "windll", falso), \
                mock.patch.object(ctypes, "wstring_at",
                                  return_value="hola\x00resto") as leer:
            self.assertEqual(clipboard._texto_windows(), "hola")
        self.assertEqual(leer.call_args[0], (0x5678, 12))

    def test_bloque_vacio_no_lee_nada(self):
        falso = self._falsos(0)
        with mock.patch.object(ctypes, "windll", falso), \
                mock.patch.object(ctypes, "wstring_at") as leer:
            self.assertIsNone(clipboard._texto_windows())
        leer.assert_not_called()


if __name__ == "__main__":
    unittest.main()

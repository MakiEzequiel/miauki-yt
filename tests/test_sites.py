# -*- coding: utf-8 -*-
"""Tests de sites.py: detección, normalización y reglas de la spec §3."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import errors  # noqa: E402
from miauki.core import sites  # noqa: E402


class Esquema(unittest.TestCase):
    def test_solo_http_https(self):
        for url in ["ftp://x.com/a", "javascript:alert(1)", "hola mundo",
                    "file:///c:/x", "//x.com/a", ""]:
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                sites.detectar(url)
            self.assertEqual(ctx.exception.codigo, "link_invalido", url)

    def test_http_y_https_pasan(self):
        self.assertEqual(sites.detectar("http://youtu.be/abc")[0], "youtube")
        self.assertEqual(sites.detectar("https://youtu.be/abc")[0], "youtube")


class YouTube(unittest.TestCase):
    def test_video_con_lista_da_un_solo_video(self):
        sitio, url = sites.detectar(
            "https://www.youtube.com/watch?v=pCPYb7KPoUc&list=RDpCPYb7KPoUc&index=1")
        self.assertEqual(sitio, "youtube")
        self.assertEqual(url, "https://www.youtube.com/watch?v=pCPYb7KPoUc")

    def test_playlist_se_canonicaliza(self):
        sitio, url = sites.detectar("https://www.youtube.com/playlist?list=PLxxxx")
        self.assertEqual(sitio, "youtube")
        self.assertEqual(url, "https://www.youtube.com/playlist?list=PLxxxx")

    def test_playlist_music_se_canonicaliza(self):
        sitio, url = sites.detectar(
            "https://music.youtube.com/playlist?list=PLxxxx&feature=share")
        self.assertEqual(sitio, "youtube")
        self.assertEqual(url, "https://music.youtube.com/playlist?list=PLxxxx")

    def test_playlist_con_params_extra_se_canonicaliza(self):
        sitio, url = sites.detectar(
            "https://www.youtube.com/playlist?list=PLxxxx&si=abc")
        self.assertEqual(sitio, "youtube")
        self.assertEqual(url, "https://www.youtube.com/playlist?list=PLxxxx")

    def test_portada_y_canales_dan_no_es_video(self):
        for url in ["https://www.youtube.com/",
                    "https://www.youtube.com/@StereoHodler",
                    "https://www.youtube.com/channel/UC123",
                    "https://m.youtube.com/"]:
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                sites.detectar(url)
            self.assertEqual(ctx.exception.codigo, "no_es_video", url)

    def test_corto_youtu_be_se_canonicaliza(self):
        sitio, url = sites.detectar("https://youtu.be/abc123?t=42")
        self.assertEqual((sitio, url), ("youtube", "https://www.youtube.com/watch?v=abc123"))

    def test_watch_sin_v_es_link_invalido(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            sites.detectar("https://www.youtube.com/watch?utm=1")
        self.assertEqual(ctx.exception.codigo, "link_invalido")

    def test_playlist_sin_codigo_da_mensaje_claro(self):
        # Caso real del 20/11/2026: youtube.com/playlist suelto salía como
        # "el motor no devolvió datos"; ahora tiene su propio mensaje.
        for url in ("https://youtube.com/playlist",
                    "https://www.youtube.com/playlist?list="):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                sites.detectar(url)
            self.assertEqual(ctx.exception.codigo, "playlist_sin_id", url)


class Facebook(unittest.TestCase):
    def test_link_compartido_share_r(self):
        sitio, url = sites.detectar("https://www.facebook.com/share/r/1PonqKC4oQ/")
        self.assertEqual(sitio, "facebook")
        self.assertEqual(url, "https://www.facebook.com/share/r/1PonqKC4oQ/")

    def test_foto_con_fbid_se_conserva(self):
        sitio, url = sites.detectar("https://www.facebook.com/photo/?fbid=1111696508036243")
        self.assertEqual(sitio, "facebook")
        self.assertIn("fbid=1111696508036243", url)

    def test_tracking_fuera_ids_dentro(self):
        sitio, url = sites.detectar(
            "https://www.facebook.com/permalink.php?story_fbid=99&id=55"
            "&__cft__=zzz&fbclid=www&mibextid=abc")
        self.assertEqual(sitio, "facebook")
        self.assertIn("story_fbid=99", url)
        self.assertIn("id=55", url)
        self.assertNotIn("__cft__", url)
        self.assertNotIn("fbclid", url)
        self.assertNotIn("mibextid", url)

    def test_portada_dan_no_es_video(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            sites.detectar("https://www.facebook.com/")
        self.assertEqual(ctx.exception.codigo, "no_es_video")


class OtrosSitios(unittest.TestCase):
    def test_tiktok_portada_con_idioma_dan_no_es_video(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            sites.detectar("https://www.tiktok.com/es/")
        self.assertEqual(ctx.exception.codigo, "no_es_video")

    def test_tiktok_reel_pasa(self):
        self.assertEqual(sites.detectar("https://www.tiktok.com/@u/video/7123")[0],
                         "tiktok")

    def test_instagram_reel(self):
        self.assertEqual(
            sites.detectar("https://www.instagram.com/reel/Def341BAmx8/?obrf=1")[0],
            "instagram")

    def test_instagram_portada_dan_no_es_video(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            sites.detectar("https://instagram.com/")
        self.assertEqual(ctx.exception.codigo, "no_es_video")

    def test_instagram_stories_url_pasa(self):
        """Plan `plan.md`, paso 1.3: un story no es raíz y llega al motor."""
        sitio, url = sites.detectar(
            "https://www.instagram.com/stories/usuario/12345/")
        self.assertEqual(sitio, "instagram")
        self.assertIn("/stories/usuario/12345", url)

    def test_instagram_perfil_publico_pasa(self):
        """Plan `plan.md`, paso 2.1: el perfil es una lista de posts."""
        sitio, url = sites.detectar("https://www.instagram.com/maki/")
        self.assertEqual(sitio, "instagram")
        self.assertEqual(url, "https://www.instagram.com/maki/")

    def test_instagram_codigo_idioma_sigue_bloqueado(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            sites.detectar("https://www.instagram.com/es/")
        self.assertEqual(ctx.exception.codigo, "no_es_video")

    def test_instagram_usuario_de_dos_letras_no_es_idioma(self):
        """La lista de idiomas es explícita: /mk/ es un perfil, no la portada."""
        sitio, _ = sites.detectar("https://www.instagram.com/mk/")
        self.assertEqual(sitio, "instagram")

    def test_x_con_foto(self):
        sitio, url = sites.detectar(
            "https://x.com/StereoHodler/status/2110183275461513256/photo/1")
        self.assertEqual(sitio, "x")
        self.assertIn("/status/2110183275461513256/photo/1", url)

    def test_twitter_viejo_tambien_es_x(self):
        self.assertEqual(sites.detectar("https://twitter.com/u/status/1")[0], "x")

    def test_sitio_desconocido_pasa_como_otro(self):
        sitio, url = sites.detectar("https://ejemplo.com/ver/video1")
        self.assertEqual((sitio, url), ("otro", "https://ejemplo.com/ver/video1"))


class Normalizacion(unittest.TestCase):
    def test_host_minusculas_sin_fragmento(self):
        sitio, url = sites.detectar("https://WWW.YouTube.com/watch?v=abc#parte")
        self.assertEqual(sitio, "youtube")
        self.assertEqual(url, "https://www.youtube.com/watch?v=abc")

    def test_no_se_hace_host_falso(self):
        self.assertEqual(sites.detectar("https://noyoutube.com/watch?v=abc")[0], "otro")

    def test_detectar_www_instagram(self):
        """Plan `plan.md`, paso 3.2: `www.` sin esquema se normaliza."""
        self.assertEqual(sites.detectar("www.instagram.com/maki/"),
                         ("instagram", "https://www.instagram.com/maki/"))

    def test_detectar_dominio_desnudo(self):
        self.assertEqual(sites.detectar("minombre.io/video"),
                         ("otro", "https://minombre.io/video"))

    def test_detectar_sin_path_rechaza(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            sites.detectar("minombre.io")
        self.assertEqual(ctx.exception.codigo, "link_invalido")


if __name__ == "__main__":
    unittest.main()

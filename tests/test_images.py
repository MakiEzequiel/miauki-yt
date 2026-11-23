# -*- coding: utf-8 -*-
"""Tests de images.py: descarga segura sin red (A6) + vías de X/Facebook (B5/A5)."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import base64
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import analyzer, errors, images  # noqa: E402

AJUSTES = {"fxtwitter": True, "navegador_cookies": "ninguno"}
URL_X = "https://x.com/StereoHodler/status/2110183275461513256/photo/1"

GRAPHQL_OK = json.dumps({
    "data": {"tweetResult": {"result": {
        "__typename": "Tweet",
        "legacy": {
            "full_text": "Foto linda del atardecer",
            "extended_entities": {"media": [
                {"type": "photo",
                 "media_url_https": "https://pbs.twimg.com/media/AbC123.jpg?format=jpg&name=small"},
                {"type": "photo",
                 "media_url_https": "https://pbs.twimg.com/media/Def456.jpg?format=jpg&name=small"},
            ]},
        },
        "core": {"user_results": {"result": {"legacy": {
            "name": "Stereo Hodler", "screen_name": "StereoHodler"}}}},
    }}},
})
SYND_OK = json.dumps({
    "text": "Otra foto",
    "user": {"name": "Pepe", "screen_name": "pepe"},
    "mediaDetails": [{"type": "photo",
                      "media_url_https": "https://pbs.twimg.com/media/SyNd1.jpg"}],
})
FX_OK = json.dumps({
    "code": 200,
    "tweet": {"text": "Desde Fx", "author": {"screen_name": "pepe", "name": "Pepe"},
              "media": {"all": [{"type": "photo", "url": "https://pbs.twimg.com/media/Fx1.jpg"}]}},
})
PROTEGIDO = json.dumps({"data": {"tweetResult": {"result": {
    "__typename": "TweetUnavailable", "reason": "Protected"}}}})
SIN_MEDIO = json.dumps({
    "data": {"tweetResult": {"result": {
        "__typename": "Tweet",
        "legacy": {"full_text": "solo texto", "extended_entities": {"media": []}},
        "core": {"user_results": {"result": {"legacy": {"name": "Pepe", "screen_name": "pepe"}}}},
    }}},
})
SIN_MEDIA_DETAILS = json.dumps({"text": "solo texto", "user": {"name": "Pepe", "screen_name": "pepe"}})
GRAPHQL_VIDEO = json.dumps({
    "data": {"tweetResult": {"result": {
        "__typename": "Tweet",
        "legacy": {"full_text": "Video del post", "extended_entities": {"media": [{
            "type": "video",
            "media_url_https": "https://pbs.twimg.com/thumb.jpg",
            "video_info": {"duration_millis": 10000, "variants": [
                {"url": "https://video.twimg.com/vid/avc1/480x270/b360.mp4",
                 "bitrate": 288000, "content_type": "video/mp4"},
                {"url": "https://video.twimg.com/vid/avc1/1280x720/b720.mp4",
                 "bitrate": 832000, "content_type": "video/mp4"},
                {"url": "https://video.twimg.com/b/play.m3u8", "bitrate": 0,
                 "content_type": "application/x-mpegURL"},
            ]},
        }]}},
        "core": {"user_results": {"result": {"legacy": {
            "name": "Pepe", "screen_name": "pepe"}}}},
    }}},
})
SYND_VIDEO = json.dumps({
    "text": "Video sindicado",
    "user": {"name": "Pepe", "screen_name": "pepe"},
    "mediaDetails": [{
        "type": "video",
        "media_url_https": "https://pbs.twimg.com/thumb2.jpg",
        "video_info": {"variants": [
            {"url": "https://video.twimg.com/vid/avc1/640x360/c480.mp4",
             "bitrate": 832000, "content_type": "video/mp4"},
        ]},
    }],
})
FX_VIDEO = json.dumps({
    "code": 200,
    "tweet": {"text": "Video desde Fx", "author": {"screen_name": "pepe", "name": "Pepe"},
              "media": {"all": [{
                  "type": "video",
                  "url": "https://video.twimg.com/vid/avc1/1280x720/a1280.mp4",
                  "format": "video/mp4",
                  "duration": 12.5,
                  "thumbnail_url": "https://pbs.twimg.com/thumb3.jpg",
                  "variants": [
                      {"url": "https://video.twimg.com/pl/play.m3u8",
                       "container": "m3u8"},
                      {"url": "https://video.twimg.com/vid/avc1/480x270/a480.mp4",
                       "bitrate": 288000, "content_type": "video/mp4"},
                      {"url": "https://video.twimg.com/vid/avc1/1280x720/a1280.mp4",
                       "bitrate": 2176000, "content_type": "video/mp4"},
                  ],
              }]}},
})


def con_respuestas(respuestas):
    """_pedir falso: responde por fragmento de URL (sin red, A6)."""
    def pedir(url, headers=None, data=None, timeout=None):
        for fragmento, respuesta in respuestas.items():
            if fragmento in url:
                status, cuerpo = respuesta
                return status, cuerpo.encode() if isinstance(cuerpo, str) else cuerpo
        raise AssertionError("URL no prevista en el test: %s" % url)
    return pedir


class Ips(unittest.TestCase):
    def test_ips_publicas_pasan(self):
        self.assertTrue(images._ip_ok("8.8.8.8"))
        self.assertTrue(images._ip_ok("1.1.1.1"))
        self.assertTrue(images._ip_ok("2001:4860:4860::8888"))

    def test_ips_privadas_y_locales_no_pasan(self):
        for ip in ["192.168.1.5", "10.0.0.1", "172.16.0.9", "127.0.0.1",
                   "169.254.10.10", "::1", "fe80::1", "0.0.0.0",
                   "::ffff:192.168.0.1"]:
            self.assertFalse(images._ip_ok(ip), ip)

    def test_ipv4_mapeada_privada_tampoco(self):
        self.assertFalse(images._ip_ok("::ffff:127.0.0.1"))


class Whitelist(unittest.TestCase):
    def test_solo_https_de_dominios_de_la_lista(self):
        self.assertTrue(images._permitido("https://i.ytimg.com/vi/x/hq.jpg"))
        self.assertTrue(images._permitido("https://img.youtube.com/x"))
        self.assertFalse(images._permitido("http://i.ytimg.com/x"))
        self.assertFalse(images._permitido("https://evil.com/i.ytimg.com"))
        self.assertFalse(images._permitido("https://i.ytimg.com.evil.com/x"))
        self.assertFalse(images._permitido("file:///c:/x.jpg"))

    def test_cdn_snapchat_en_whitelist(self):
        self.assertTrue(images._permitido(
            "https://bolt-gcdn.sc-cdn.net/s/I9czmjfMAKlnt7sKP10RR.256.IRZXSOY"))
        self.assertTrue(images._permitido("https://sc-cdn.net/x"))
        self.assertFalse(images._permitido("https://sc-cdn.net.evil.com/x"))
        self.assertFalse(images._permitido("https://evil.com/sc-cdn.net/x"))


class DataUri(unittest.TestCase):
    def test_imagen_ok_se_vuelve_data_uri(self):
        with mock.patch.object(images, "_ips_ok", return_value=True), \
             mock.patch.object(images, "_OPENER") as op:
            r = mock.Mock()
            r.headers = {"Content-Type": "image/jpeg"}
            r.read.return_value = b"\xff\xd8hola"
            op.open.return_value = r
            out = images.data_uri_de("https://i.ytimg.com/vi/x/hq.jpg")
        self.assertEqual(
            out,
            "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8hola").decode(),
        )

    def test_data_uri_cdn_snapchat(self):
        with mock.patch.object(images, "_ips_ok", return_value=True), \
             mock.patch.object(images, "_OPENER") as op:
            r = mock.Mock()
            r.headers = {"Content-Type": "image/jpeg"}
            r.read.return_value = b"\xff\xd8spotlight"
            op.open.return_value = r
            out = images.data_uri_de(
                "https://bolt-gcdn.sc-cdn.net/s/I9czmjfMAKlnt7sKP10RR.256.IRZXSOY")
        self.assertEqual(
            out,
            "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8spotlight").decode(),
        )

    def test_html_no_pasa_por_imagen(self):
        with mock.patch.object(images, "_ips_ok", return_value=True), \
             mock.patch.object(images, "_OPENER") as op:
            r = mock.Mock()
            r.headers = {"Content-Type": "text/html; charset=utf-8"}
            r.read.return_value = b"<html>"
            op.open.return_value = r
            self.assertIsNone(images.data_uri_de("https://i.ytimg.com/x"))

    def test_ip_privada_da_none(self):
        with mock.patch.object(images, "_ips_ok", return_value=False):
            self.assertIsNone(images.data_uri_de("https://i.ytimg.com/x"))

    def test_salto_a_http_no_se_sigue(self):
        with mock.patch.object(images, "_ips_ok", return_value=True), \
             mock.patch.object(images, "_OPENER") as op:
            op.open.side_effect = urllib.error.HTTPError(
                "https://i.ytimg.com/x", 302, "Found",
                {"Location": "http://interno/archivo.jpg"}, io.BytesIO(b""))
            self.assertIsNone(images.data_uri_de("https://i.ytimg.com/x"))

    def test_salto_fuera_de_whitelist_no_se_sigue(self):
        with mock.patch.object(images, "_ips_ok", return_value=True), \
             mock.patch.object(images, "_OPENER") as op:
            op.open.side_effect = urllib.error.HTTPError(
                "https://i.ytimg.com/x", 301, "Moved",
                {"Location": "https://scontent.evil.net/x.jpg"}, io.BytesIO(b""))
            self.assertIsNone(images.data_uri_de("https://i.ytimg.com/x"))

    def test_url_que_explota_da_none(self):
        with mock.patch.object(images, "_ips_ok", side_effect=OSError("sin dns")):
            self.assertIsNone(images.data_uri_de("https://i.ytimg.com/x"))


class ParseoTweet(unittest.TestCase):
    def test_id_desde_x_con_foto(self):
        self.assertEqual(images.id_tweet(URL_X), "2110183275461513256")

    def test_id_desde_otro_host_de_x(self):
        self.assertEqual(
            images.id_tweet("https://vxtwitter.com/a/status/987654321098765432"),
            "987654321098765432")

    def test_id_desde_twitter_com_con_query(self):
        self.assertEqual(
            images.id_tweet("https://twitter.com/a/status/123456789?s=20"),
            "123456789")

    def test_sin_id_da_error_amable(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            images.id_tweet("https://x.com/pepe/status/sin-id")
        self.assertEqual(ctx.exception.codigo, "link_invalido")


class ViasX(unittest.TestCase):
    """A5: misma interfaz, orden configurable, log de vía usada/fallidas."""

    def setUp(self):
        images._token_invitado = None
        self.log = mock.MagicMock()
        parche = mock.patch.object(images, "obtener_logger", return_value=self.log)
        parche.start()
        self.addCleanup(parche.stop)

    def test_graphql_primero_y_lista_completa(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (200, GRAPHQL_OK),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(r["via"], "graphql")
        self.assertEqual(r["sitio"], "x")
        self.assertEqual(len(r["imagenes"]), 2)
        self.assertTrue(all(u.startswith("https://pbs.twimg.com/") for u in r["imagenes"]))
        self.assertTrue(all("name=4096x4096" in u for u in r["imagenes"]))
        self.assertEqual(r["autor"], "Stereo Hodler")
        self.assertEqual(r["titulo"], "Stereo Hodler - Foto linda del atardecer")

    def test_graphql_falla_syndication_salva_y_se_loguea(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (403, "{}"),
            "cdn.syndication.twimg.com": (200, SYND_OK),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(r["via"], "syndication")
        self.assertEqual(r["imagenes"],
                         ["https://pbs.twimg.com/media/SyNd1.jpg?name=4096x4096"])
        texto_log = " ".join(str(c) for c in self.log.info.call_args_list)
        self.assertIn("graphql", texto_log)

    def test_fx_respaldo_cuando_las_dos_fallan(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (403, "{}"),
            "cdn.syndication.twimg.com": (404, "no"),
            "api.fxtwitter.com": (200, FX_OK),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(r["via"], "fxtwitter")
        self.assertEqual(r["imagenes"], ["https://pbs.twimg.com/media/Fx1.jpg?name=4096x4096"])
        self.assertEqual(r["autor"], "pepe")

    def test_fx_deshabilitada_no_se_pide(self):
        llamadas = []

        def pedir(url, headers=None, data=None, timeout=None):
            llamadas.append(url)
            if "guest/activate.json" in url:
                return 200, b'{"guest_token": "77"}'
            if "TweetResultByRestId" in url:
                return 403, b"{}"
            if "syndication" in url:
                return 404, b"no"
            raise AssertionError("URL inesperada: %s" % url)

        ajustes = dict(AJUSTES, fxtwitter=False)
        with mock.patch.object(images, "_pedir", side_effect=pedir):
            with self.assertRaises(errors.ErrorMiauki):
                images.imagenes_de(URL_X, ajustes)
        self.assertFalse(any("fxtwitter" in u for u in llamadas))

    def test_tweet_protegido_sugiere_cookies(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (200, PROTEGIDO),
            "cdn.syndication.twimg.com": (404, "no"),
        })):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                images.imagenes_de(URL_X, dict(AJUSTES, fxtwitter=False))
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")
        self.assertIn("cookies", ctx.exception.mensaje.lower())

    def test_tweet_solo_texto_da_no_es_video(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (200, SIN_MEDIO),
            "cdn.syndication.twimg.com": (200, SIN_MEDIA_DETAILS),
        })):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                images.imagenes_de(URL_X, dict(AJUSTES, fxtwitter=False))
        self.assertEqual(ctx.exception.codigo, "no_es_video")

    def test_graphql_video_da_es_video(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (200, GRAPHQL_VIDEO),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(r["via"], "graphql")
        self.assertTrue(r["es_video"])
        self.assertEqual(r["imagenes"],
                         ["https://video.twimg.com/vid/avc1/1280x720/b720.mp4"])
        self.assertEqual(r["video"]["duracion"], 10.0)
        self.assertEqual(r["video"]["miniatura"], "https://pbs.twimg.com/thumb.jpg")

    def test_syndication_video_da_es_video(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (403, "{}"),
            "cdn.syndication.twimg.com": (200, SYND_VIDEO),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(r["via"], "syndication")
        self.assertTrue(r["es_video"])
        self.assertEqual(r["imagenes"],
                         ["https://video.twimg.com/vid/avc1/640x360/c480.mp4"])

    def test_fx_video_da_es_video_y_la_mejor_calidad(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (403, "{}"),
            "cdn.syndication.twimg.com": (404, "no"),
            "api.fxtwitter.com": (200, FX_VIDEO),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(r["via"], "fxtwitter")
        self.assertTrue(r["es_video"])
        self.assertEqual(r["imagenes"],
                         ["https://video.twimg.com/vid/avc1/1280x720/a1280.mp4"])
        # El .m3u8 no es un archivo descargable: queda afuera.
        self.assertEqual([v["alto"] for v in r["video"]["variantes"]], [720, 270])
        self.assertEqual(r["video"]["duracion"], 12.5)

    def test_fx_video_se_arma_como_video_en_el_resultado(self):
        datos = {"es_video": True, "imagenes": ["https://video.twimg.com/a/1280.mp4"],
                 "titulo": "Pepe - video", "autor": "Pepe"}
        r = analyzer._resultado_imagenes(datos, "x", URL_X)
        self.assertEqual(r["tipo"], "video")
        self.assertEqual(r["calidades"][0]["url_directa"],
                         "https://video.twimg.com/a/1280.mp4")

    def test_video_x_arma_calidades_peso_duracion_y_miniatura(self):
        datos = {
            "es_video": True, "titulo": "Pepe - video", "autor": "Pepe",
            "imagenes": ["https://video.twimg.com/vid/avc1/1280x720/a.mp4"],
            "video": {
                "url": "https://video.twimg.com/vid/avc1/1280x720/a.mp4",
                "duracion": 10.0,
                "miniatura": "https://pbs.twimg.com/thumb.jpg",
                "variantes": [
                    {"url": "https://video.twimg.com/vid/avc1/1280x720/a.mp4",
                     "bitrate": 832000, "alto": 720},
                    {"url": "https://video.twimg.com/vid/avc1/480x270/b.mp4",
                     "bitrate": 288000, "alto": 270},
                ],
            },
        }
        with mock.patch.object(images, "data_uri_de",
                               return_value="data:image/jpeg;base64,AAA"), \
             mock.patch.object(images, "peso_de_video", return_value=None):
            r = analyzer._resultado_imagenes(datos, "x", URL_X)
        self.assertEqual([c["resolucion"] for c in r["calidades"]], [720, 270])
        self.assertEqual(r["calidades"][0]["recomendada"], "La mejor")
        self.assertEqual(r["calidades"][1]["recomendada"], "Equilibrada")
        self.assertEqual(r["calidades"][0]["etiqueta"], "720p")
        self.assertEqual(r["calidades"][0]["peso_bytes"], 1040000)
        self.assertTrue(r["calidades"][0]["peso_aprox"])
        self.assertEqual(r["duracion"], 10.0)
        self.assertEqual(r["miniatura"], "data:image/jpeg;base64,AAA")
        self.assertEqual(r["imagenes_urls"],
                         ["https://pbs.twimg.com/thumb.jpg"])
        self.assertEqual(r["tipos"], ["video", "imagen"])

    def test_video_x_muestra_el_peso_real_si_el_servidor_lo_dice(self):
        datos = {
            "es_video": True, "titulo": "Pepe - video", "autor": "Pepe",
            "video": {
                "duracion": 10.0, "miniatura": "",
                "variantes": [{"url": "https://video.twimg.com/v/a.mp4",
                               "bitrate": 832000, "alto": 720}],
            },
        }
        with mock.patch.object(images, "data_uri_de", return_value=None), \
             mock.patch.object(images, "peso_de_video", return_value=19377214):
            r = analyzer._resultado_imagenes(datos, "x", URL_X)
        self.assertEqual(r["calidades"][0]["peso_bytes"], 19377214)
        self.assertFalse(r["calidades"][0]["peso_aprox"])

    def test_sitio_de_imagenes_no_soportado(self):
        with self.assertRaises(errors.ErrorMiauki) as ctx:
            images.imagenes_de("https://www.tiktok.com/es/", dict(AJUSTES))
        self.assertEqual(ctx.exception.codigo, "sitio_no_soportado")


class Facebook(unittest.TestCase):
    def test_foto_facebook_por_extractor_ytdlp(self):
        info = {"url": "https://scontent.xx.fbcdn.net/v/t1.0-0/p100x100/111.jpg?_nc_cat=1",
                "title": "Foto de Pepe", "uploader": "Pepe"}
        with mock.patch.object(analyzer, "_extraer", return_value=info):
            r = images.imagenes_de(
                "https://www.facebook.com/photo/?fbid=1111696508036243", dict(AJUSTES))
        self.assertEqual(r["sitio"], "facebook")
        self.assertEqual(r["via"], "ytdlp")
        self.assertEqual(r["imagenes"], [info["url"]])
        self.assertEqual(r["titulo"], "Foto de Pepe")
        self.assertEqual(r["autor"], "Pepe")

    def test_varias_fotos_por_entradas(self):
        info = {"entries": [
            {"url": "https://scontent.xx.fbcdn.net/a.jpg"},
            {"url": "https://scontent.xx.fbcdn.net/b.png"},
            {"url": "https://video.xx.fbcdn.net/c.mp4"},
        ]}
        with mock.patch.object(analyzer, "_extraer", return_value=info):
            r = images.imagenes_de("https://www.facebook.com/photo.php?fbid=9", dict(AJUSTES))
        self.assertEqual(r["imagenes"],
                         ["https://scontent.xx.fbcdn.net/a.jpg",
                          "https://scontent.xx.fbcdn.net/b.png"])

    def test_extractor_falla_se_mapea_a_codigo_amable(self):
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Video unavailable")):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                images.imagenes_de("https://www.facebook.com/photo.php?fbid=9", dict(AJUSTES))
        self.assertEqual(ctx.exception.codigo, "video_eliminado")

    def test_extractor_sin_fotos_reporta_la_causa(self):
        info = {"url": "https://video.xx.fbcdn.net/c.mp4", "ext": "mp4"}
        with mock.patch.object(analyzer, "_extraer", return_value=info):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                images.imagenes_de("https://www.facebook.com/photo.php?fbid=9", dict(AJUSTES))
        self.assertEqual(ctx.exception.codigo, "no_es_video")
        self.assertIn("yt-dlp", ctx.exception.mensaje.lower())


class ImagenDirectaX(unittest.TestCase):
    """Fase 9, B1: los links sueltos de pbs.twimg.com son imagen sola."""

    URL = "https://pbs.twimg.com/media/HVOZ0t7WkAAYiLP?format=jpg&name=large"

    def test_reconoce_la_url_del_cdn(self):
        self.assertTrue(images.es_imagen_x_directa(self.URL))
        self.assertTrue(images.es_imagen_x_directa(
            "https://pbs.twimg.com/media/HVKt-jPW8AAFllF?format=jpg&name=small"))

    def test_no_confunde_perfil_ni_post(self):
        self.assertFalse(images.es_imagen_x_directa(
            "https://pbs.twimg.com/profile_images/1/foto.jpg"))
        self.assertFalse(images.es_imagen_x_directa(URL_X))
        self.assertFalse(images.es_imagen_x_directa(""))

    def test_devuelve_la_foto_al_maximo(self):
        r = images.imagenes_de(self.URL, dict(AJUSTES))
        self.assertEqual(r["via"], "directa")
        self.assertEqual(r["sitio"], "x")
        self.assertEqual(r["imagenes"],
                         ["https://pbs.twimg.com/media/HVOZ0t7WkAAYiLP"
                          "?format=jpg&name=4096x4096"])

    def test_el_analisis_no_manda_la_foto_a_ytdlp(self):
        def no_llamar(*a, **k):
            raise AssertionError("yt-dlp no debe analizar una foto directa")
        with mock.patch.object(analyzer, "_extraer", side_effect=no_llamar), \
                mock.patch.object(analyzer.images, "data_uri_de",
                                  return_value="data:image/jpeg;base64,AA=="):
            r = analyzer.analizar(self.URL, forzar=True)
        self.assertEqual(r["tipo"], "imagen")
        self.assertEqual(r["tipos"], ["imagen"])
        self.assertEqual(r["sitio"], "x")
        self.assertEqual(len(r["imagenes"]), 1)


class VariantesDeLink(unittest.TestCase):
    """Fase 9, B1: mismos formatos de link que entendía la v2.6."""

    def test_formatos_conocidos(self):
        esperado = "2110183275461513256"
        for url in (
            "https://x.com/u/status/2110183275461513256/photo/1",
            "https://twitter.com/u/status/2110183275461513256",
            "https://vxtwitter.com/u/status/2110183275461513256",
            "https://fixvx.com/u/status/2110183275461513256",
            "https://fxtwitter.com/u/status/2110183275461513256",
            "https://x.com/i/mediaviewer/2110183275461513256",
            "https://x.com/u/status/2110183275461513256/video/1",
            "https://x.com/u?post_id=2110183275461513256",
        ):
            with self.subTest(url=url):
                self.assertEqual(images.id_tweet(url), esperado)

    def test_link_sin_id_avisa(self):
        with self.assertRaises(errors.ErrorMiauki):
            images.id_tweet("https://x.com/MakiEzequiel")


class BloqueoPorSesion(unittest.TestCase):
    """Fase 9, B2: sin sesión, X devuelve una lápida vacía (contenido sensible)."""

    TOMBSTONE = json.dumps({"data": {"tweetResult": {"result": {
        "__typename": "TweetTombstone"}}}})

    def test_tombstone_vacio_pide_sesion_y_no_dice_borrado(self):
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (200, self.TOMBSTONE),
            "cdn.syndication.twimg.com": (404, "no"),
        })):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                images.imagenes_de(URL_X, dict(AJUSTES, fxtwitter=False))
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")
        self.assertIn("sesión", ctx.exception.mensaje.lower())
        self.assertIn("Ajustes", ctx.exception.mensaje)

    def test_el_analisis_muestra_el_error_de_sesion_y_no_el_generico(self):
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Video #1 is unavailable")), \
                mock.patch.object(analyzer.images, "imagenes_de",
                                  side_effect=errors.ErrorMiauki(
                                      "requiere_sesion", "Pedí sesión")):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                analyzer.analizar("https://x.com/u/status/2107806784740077865/video/1",
                                  forzar=True)
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")


class FixtureReal(unittest.TestCase):
    """Fase 9, B1: fixture capturada de una corrida real y limpiada."""

    def _payload(self, fotos):
        datos = json.loads((Path(__file__).parent / "fixtures"
                            / "x_graphql_foto_real.json").read_text(encoding="utf-8"))
        media = datos["data"]["tweetResult"]["result"]["legacy"]["extended_entities"]["media"]
        base = media[0]
        while len(media) < fotos:
            media.append({"type": "photo",
                          "media_url_https": "https://pbs.twimg.com/media/Extra%d.jpg"
                                             % len(media)})
        return datos, base

    def test_una_foto_real(self):
        datos, _ = self._payload(1)
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (200, json.dumps(datos)),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(len(r["imagenes"]), 1)
        self.assertIn("pbs.twimg.com/media/HUjf8tjXQAEOlBY.jpg", r["imagenes"][0])

    def test_tres_fotos_se_devuelven_todas(self):
        datos, _ = self._payload(3)
        with mock.patch.object(images, "_pedir", side_effect=con_respuestas({
            "guest/activate.json": (200, '{"guest_token": "77"}'),
            "TweetResultByRestId": (200, json.dumps(datos)),
        })):
            r = images.imagenes_de(URL_X, dict(AJUSTES))
        self.assertEqual(len(r["imagenes"]), 3)
        self.assertEqual(len({u.split("?")[0] for u in r["imagenes"]}), 3)


class GoogleYDirectas(unittest.TestCase):
    """Auditoría 23/11: Google Imágenes (share.google / imgres) y gstatic."""

    def test_imgres_es_google_y_saca_imgurl(self):
        url = ("https://www.google.com/imgres?imgurl=https%3A%2F%2Fcdn.example.com"
               "%2Fa.jpg&tbnid=WB&vet=1")
        self.assertTrue(images.es_imagen_google(url))
        self.assertEqual(images.imgurl_de_google(url),
                         "https://cdn.example.com/a.jpg")

    def test_share_google_es_google(self):
        self.assertTrue(images.es_imagen_google("https://share.google/abc123"))
        self.assertIsNone(images.imgurl_de_google("https://share.google/abc123"))

    def test_no_es_google(self):
        self.assertFalse(images.es_imagen_google("https://example.com/imgres?a=1"))
        self.assertFalse(images.es_imagen_google("https://www.google.com/"))

    def test_gstatic_es_imagen_directa(self):
        url = ("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9Gc...&s=10")
        self.assertTrue(images.es_imagen_directa(url))
        self.assertFalse(images.es_imagen_directa("https://example.com/foto.jpg"))

    def test_anfitriones_incluye_gstatic_y_arcpublishing(self):
        self.assertIn("gstatic.com", images.ANFITRIONES)
        self.assertIn("arcpublishing.com", images.ANFITRIONES)

    def test_tiktok_foto_sin_cookies_pide_sesion(self):
        with mock.patch.object(
                images, "_og_image_de",
                side_effect=images._Falla("error_desconocido", "sin og:image")):
            with self.assertRaises(errors.ErrorMiauki) as ctx:
                images.imagenes_de(
                    "https://www.tiktok.com/@usuario/photo/7361239230305111302",
                    dict(AJUSTES))
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")
        self.assertIn("sesión", ctx.exception.mensaje.lower())
        self.assertIn("Ajustes", ctx.exception.mensaje)


if __name__ == "__main__":
    unittest.main()

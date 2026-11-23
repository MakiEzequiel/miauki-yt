# -*- coding: utf-8 -*-
"""Tests de analyzer.py: sin internet (dicts armados a mano; A2)."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import analyzer  # noqa: E402
from miauki.core import errors  # noqa: E402
from miauki.core.errors import ErrorMiauki  # noqa: E402

URL = "https://www.youtube.com/watch?v=abc123"

INFO = {
    "id": "abc123",
    "title": "Video de prueba",
    "uploader": "Canal de Prueba",
    "channel": "Canal de Prueba",
    "duration": 123,
    "webpage_url": URL,
    "thumbnail": "https://i.ytimg.com/vi/abc123/hq720.jpg",
    "subtitles": {"es": [{"ext": "vtt"}], "en": [{"ext": "vtt"}]},
    "automatic_captions": {"es": [], "fr": []},
    "formats": [
        {"format_id": "299", "height": 1080, "vcodec": "avc1.64002a",
         "acodec": "none", "tbr": 4500, "filesize": 9500000, "ext": "mp4"},
        {"format_id": "137", "height": 1080, "vcodec": "avc1.640028",
         "acodec": "none", "tbr": 4000, "filesize": 9000000, "ext": "mp4"},
        {"format_id": "248", "height": 1080, "vcodec": "vp09.00.10.08",
         "acodec": "none", "tbr": 3500, "filesize": 8000000, "ext": "webm"},
        {"format_id": "136", "height": 720, "vcodec": "avc1.4d401f",
         "acodec": "none", "tbr": 2500, "filesize": 6000000, "ext": "mp4"},
        {"format_id": "135", "height": 480, "vcodec": "avc1.4d401e",
         "acodec": "none", "tbr": 1200, "filesize": 3000000, "ext": "mp4"},
        {"format_id": "18", "height": 360, "vcodec": "avc1.42001E",
         "acodec": "mp4a.40.2", "tbr": 500, "filesize": 1000000, "ext": "mp4"},
        {"format_id": "140", "height": None, "vcodec": "none",
         "acodec": "mp4a.40.2", "tbr": 128, "filesize": 2000000, "ext": "m4a"},
        {"format_id": "251", "height": None, "vcodec": "none",
         "acodec": "opus", "tbr": 160, "filesize": 2500000, "ext": "webm"},
    ],
}

AJUSTES = {"navegador_cookies": "ninguno", "idioma_subs": "es"}


def _info(**cambios):
    d = dict(INFO)
    d.update(cambios)
    return d


class Resultado(unittest.TestCase):
    def setUp(self):
        mini = mock.patch.object(analyzer.images, "data_uri_de",
                                 return_value=None)
        mini.start()
        self.addCleanup(mini.stop)
        self.r = analyzer._resultado_de(INFO, "youtube", URL)

    def test_campos_basicos(self):
        self.assertEqual(self.r["sitio"], "youtube")
        self.assertEqual(self.r["tipo"], "video")
        self.assertEqual(self.r["tipos"], ["video", "musica", "imagen"])
        self.assertEqual(self.r["titulo"], "Video de prueba")
        self.assertEqual(self.r["autor"], "Canal de Prueba")
        self.assertEqual(self.r["duracion"], 123)
        self.assertEqual(self.r["url_canonica"], URL)
        self.assertTrue(self.r["id_solicitud"])

    def test_subtitulos_con_ids_manuales(self):
        self.assertEqual(self.r["subtitulos"],
                         {"disponible": True, "idiomas": ["es", "en"]})

    def test_sin_manuales_usa_automaticos_con_advertencia(self):
        r = analyzer._resultado_de(
            _info(subtitles={}), "youtube", URL)
        self.assertTrue(r["subtitulos"]["disponible"])
        self.assertEqual(r["subtitulos"]["idiomas"], ["es", "fr"])
        self.assertTrue(any("autom" in a for a in r["advertencias"]))

    def test_sin_subtitulos(self):
        r = analyzer._resultado_de(
            _info(subtitles={}, automatic_captions={}), "youtube", URL)
        self.assertEqual(r["subtitulos"],
                         {"disponible": False, "idiomas": []})

    def test_calidades_recomendadas_con_selector_y_contenedor(self):
        c = {o["etiqueta"]: o for o in self.r["calidades"]}
        self.assertIn("1080p", c)
        self.assertIn("720p", c)
        self.assertIn("480p", c)
        self.assertIn("360p", c)
        mejor = c["1080p"]
        self.assertEqual(mejor["recomendada"], "La mejor")
        # política (Fase 3B 0b d): si existe H.264+AAC a esa resolución va
        # mp4; el selector va por altura+códec con respaldos (P0.5), nunca
        # por IDs de formato.
        self.assertIn("height<=1080", mejor["selector"])
        self.assertIn("vcodec^=avc1", mejor["selector"])
        self.assertIn("bestaudio", mejor["selector"])
        self.assertEqual(mejor["contenedor"], "mp4")
        self.assertEqual(mejor["peso_bytes"], 9500000 + 2000000)
        self.assertFalse(mejor["peso_aprox"])
        # Nueva regla (08/11): recomendadas = [min(max,8K), 1080, 480] con dedupe.
        # Para max=1080 → [1080, 1080, 480] → dedupe a 1080 y 480.
        # 1080p → "La mejor", 480p → "Equilibrada", 720p/360p → sin etiqueta (extendidas).
        self.assertIsNone(c["720p"]["recomendada"])
        self.assertIn("height<=720", c["720p"]["selector"])
        self.assertEqual(c["480p"]["recomendada"], "Equilibrada")

    def test_progresivo_prefiere_el_mp4_compatible(self):
        solo = _info(formats=[
            {"format_id": "b251", "height": 720, "vcodec": "vp09.00.10.08",
             "acodec": "opus", "tbr": 3000, "filesize": 5000000},
            {"format_id": "22", "height": 720, "vcodec": "avc1.4d401f",
             "acodec": "mp4a.40.2", "tbr": 2500, "filesize": 4000000},
        ])
        r = analyzer._resultado_de(solo, "youtube", URL)
        op = r["calidades"][0]
        self.assertIn("height<=720", op["selector"])
        self.assertIn("vcodec^=avc1", op["selector"])
        self.assertEqual(op["contenedor"], "mp4")

    def test_sin_compatible_mp4_usa_mkv(self):
        solo = _info(formats=[
            {"format_id": "251", "height": 2160, "vcodec": "vp09.00.50.00",
             "acodec": "none", "tbr": 20000, "filesize": 50000000},
            {"format_id": "249", "height": None, "vcodec": "none",
             "acodec": "opus", "tbr": 128, "filesize": 3000000},
        ])
        r = analyzer._resultado_de(solo, "youtube", URL)
        op = r["calidades"][0]
        self.assertIn("height<=2160", op["selector"])
        self.assertNotIn("avc1", op["selector"])     # vía mkv, sin H.264
        self.assertEqual(op["contenedor"], "mkv")

    def test_progresivo_en_mp4_no_se_anuncia_como_mkv(self):
        """TikTok manda H.265 progresivo en mp4: el contenedor es el real."""
        solo = _info(formats=[
            {"format_id": "bytevc1_1080p", "width": 1080, "height": 1920,
             "vcodec": "h265", "acodec": "aac", "tbr": 1329,
             "filesize": 1763250, "ext": "mp4"},
        ])
        r = analyzer._resultado_de(solo, "tiktok", URL)
        op = r["calidades"][0]
        self.assertEqual(op["contenedor"], "mp4")
        self.assertEqual(op["etiqueta"], "1080p")

    def test_el_filtro_por_ancho_va_primero(self):
        """Vertical: si manda el alto, se baja 576p cuando se pide 1080p."""
        self.assertLess(analyzer._selector_video(1080, False).index("width<=1080"),
                        analyzer._selector_video(1080, False).index("height<=1080"))
        self.assertLess(analyzer._selector_video(1080, True).index("width<=1080"),
                        analyzer._selector_video(1080, True).index("height<=1080"))

    def test_video_vertical_se_etiqueta_por_el_lado_corto(self):
        vertical = _info(formats=[
            {"format_id": "v1", "width": 1080, "height": 1920,
             "vcodec": "avc1.640028", "acodec": "none", "tbr": 4000,
             "filesize": 9000000, "ext": "mp4"},
            {"format_id": "a1", "width": None, "height": None,
             "vcodec": "none", "acodec": "mp4a.40.2", "tbr": 128,
             "filesize": 2000000, "ext": "m4a"},
        ])
        r = analyzer._resultado_de(vertical, "youtube", URL)
        op = r["calidades"][0]
        self.assertEqual(op["etiqueta"], "1080p")
        self.assertEqual(op["resolucion"], 1080)
        self.assertEqual(op["recomendada"], "La mejor")
        # vertical: el filtro por ancho cubre el lado corto (alto real 1920)
        self.assertIn("width<=1080", op["selector"])

    def test_peso_por_filesize_approx_marca_aproximado(self):
        aprox = _info(formats=[
            {"format_id": "136", "height": 720, "vcodec": "avc1.4d401f",
             "acodec": "none", "filesize_approx": 6100000, "ext": "mp4"},
            {"format_id": "140", "height": None, "vcodec": "none",
             "acodec": "mp4a.40.2", "filesize_approx": 2100000, "ext": "m4a"},
        ])
        r = analyzer._resultado_de(aprox, "youtube", URL)
        op = r["calidades"][0]
        self.assertEqual(op["peso_bytes"], 6100000 + 2100000)
        self.assertTrue(op["peso_aprox"])

    def test_video_pone_la_miniatura_en_imagenes(self):
        with mock.patch.object(analyzer.images, "data_uri_de",
                               return_value="data:image/jpeg;base64,xx"):
            r = analyzer._resultado_de(INFO, "youtube", URL)
        self.assertEqual(r["imagenes"], ["data:image/jpeg;base64,xx"])
        self.assertEqual(r["miniatura"], "data:image/jpeg;base64,xx")
        # data: es solo para mostrar (CSP); la URL real va aparte para
        # encolar la descarga (decisión 3d.13).
        self.assertEqual(r["imagenes_urls"], [INFO["thumbnail"]])

    def test_calidad_progresiva_es_un_solo_formato(self):
        solo = _info(formats=[
            {"format_id": "18", "height": 360, "vcodec": "avc1.42001E",
             "acodec": "mp4a.40.2", "tbr": 500, "filesize": 1000000},
        ])
        r = analyzer._resultado_de(solo, "youtube", URL)
        self.assertEqual(len(r["calidades"]), 1)
        op = r["calidades"][0]
        self.assertIn("height<=360", op["selector"])
        self.assertEqual(op["contenedor"], "mp4")
        self.assertEqual(op["recomendada"], "La mejor")

    def test_un_solo_formato_sin_metadatos_ofrece_original(self):
        """Paso 3: Snapchat manda 1 formato sin height/vcodec/tbr → 'Original'."""
        snap = _info(formats=[
            {"format_id": "0", "url": "https://cdn.sc-cdn.net/x?token=abc",
             "vcodec": None, "acodec": None, "tbr": None, "height": None,
             "width": None, "filesize_approx": None, "protocol": "https"},
        ])
        r = analyzer._resultado_de(snap, "snapchat", URL)
        self.assertEqual(len(r["calidades"]), 1)
        op = r["calidades"][0]
        self.assertEqual(op["etiqueta"], "Original")
        self.assertEqual(op["selector"], "best")
        self.assertIsNone(op["peso_bytes"])
        self.assertEqual(r["tipo"], "video")
        self.assertIn("video", r["tipos"])
        self.assertEqual(r["advertencias"],
                         ["No se detectó la resolución del video"])

    def test_snapchat_original_con_peso_real_via_head(self):
        """Snapchat 'Original' usa images.peso_de_video para peso real (no inventado)."""
        snap = _info(formats=[
            {"format_id": "0", "url": "https://bolt-gcdn.sc-cdn.net/video.mp4",
             "vcodec": None, "acodec": None, "tbr": None, "height": None,
             "width": None, "filesize_approx": None, "protocol": "https"},
        ])
        with mock.patch.object(analyzer.images, "peso_de_video",
                               return_value=12345678):
            r = analyzer._resultado_de(snap, "snapchat", URL)
        op = r["calidades"][0]
        self.assertEqual(op["etiqueta"], "Original")
        self.assertEqual(op["peso_bytes"], 12345678)
        self.assertFalse(op["peso_aprox"])
        self.assertEqual(op["url_directa"], "https://bolt-gcdn.sc-cdn.net/video.mp4")

    def test_peso_por_bitrate_marca_aproximado(self):
        sin_peso = _info(formats=[dict(f) for f in INFO["formats"]])
        for f in sin_peso["formats"]:
            f.pop("filesize", None)
        r = analyzer._resultado_de(sin_peso, "youtube", URL)
        op = {o["etiqueta"]: o for o in r["calidades"]}["720p"]
        # el audio elegido es el 140 (mp4a, preferido por la política mp4)
        esperado = int((2500 + 128) * 1000 * 123 / 8)
        self.assertEqual(op["peso_bytes"], esperado)
        self.assertTrue(op["peso_aprox"])

    def test_musica_tres_bitrates_como_mp3(self):
        m = self.r["musica"]
        self.assertEqual([x["kbps"] for x in m], [320])
        for x in m:
            self.assertEqual(x["postproceso"], "mp3")
            self.assertEqual(x["selector"], "bestaudio")
            self.assertTrue(x["peso_aprox"])
            self.assertEqual(x["peso_bytes"],
                             int(123 * x["kbps"] * 1000 / 8))
            self.assertIn("no mejora", x["advertencia"])

    def test_miniatura_se_pide_como_data_uri(self):
        with mock.patch.object(analyzer.images, "data_uri_de",
                               return_value="data:image/jpeg;base64,xx") as d:
            r = analyzer._resultado_de(INFO, "youtube", URL)
        d.assert_called_once_with(INFO["thumbnail"])
        self.assertEqual(r["miniatura"], "data:image/jpeg;base64,xx")

    def test_imagen_directa(self):
        img = {"ext": "jpg", "url": "https://i.ytimg.com/x.jpg",
               "webpage_url": URL}
        r = analyzer._resultado_de(img, "x", URL)
        self.assertEqual(r["tipo"], "imagen")
        self.assertEqual(r["tipos"], ["imagen"])
        self.assertEqual(r["calidades"], [])
        self.assertEqual(r["musica"], [])
        self.assertEqual(r["imagenes_urls"], ["https://i.ytimg.com/x.jpg"])

    def test_lista_de_imagenes(self):
        lista = {"_type": "playlist", "entries": [
            {"url": "https://i.ytimg.com/1.jpg", "ext": "jpg"},
            {"url": "https://i.ytimg.com/2.jpg", "ext": "jpg"},
        ]}
        r = analyzer._resultado_de(lista, "x", URL)
        self.assertEqual(r["tipo"], "imagen")
        self.assertEqual(r["imagenes"],
                         ["https://i.ytimg.com/1.jpg", "https://i.ytimg.com/2.jpg"])
        self.assertEqual(r["imagenes_urls"], r["imagenes"])

    def test_instagram_story_solo_imagen(self):
        """Plan `plan.md`, paso 1.2: story con ext de imagen y sin formatos."""
        story = {"formats": [], "ext": "jpg",
                 "url": "https://cdninstagram.com/x.jpg",
                 "title": "Story by maki"}
        r = analyzer._resultado_de(
            story, "instagram", "https://www.instagram.com/stories/maki/1/")
        self.assertEqual(r["tipo"], "imagen")
        self.assertEqual(r["tipos"], ["imagen"])
        self.assertEqual(r["calidades"], [])
        self.assertEqual(r["musica"], [])
        self.assertEqual(r["imagenes_urls"], ["https://cdninstagram.com/x.jpg"])

    def test_instagram_story_con_thumbnail(self):
        """Story sin `url` ni ext: la foto es la miniatura más grande."""
        story = {"formats": [], "title": "Story by maki", "thumbnails": [
            {"url": "https://cdninstagram.com/chica.jpg", "width": 320,
             "height": 568},
            {"url": "https://cdninstagram.com/grande.jpg", "width": 1080,
             "height": 1920},
        ]}
        with mock.patch.object(analyzer.images, "data_uri_de",
                               return_value="data:image/jpeg;base64,AAA"):
            r = analyzer._resultado_de(story, "instagram", URL)
        self.assertEqual(r["tipo"], "imagen")
        self.assertEqual(r["imagenes_urls"], ["https://cdninstagram.com/grande.jpg"])
        self.assertEqual(r["imagenes"], ["data:image/jpeg;base64,AAA"])


class Playlist(unittest.TestCase):
    def test_playlist_de_videos(self):
        e1 = dict(INFO)
        e1["id"] = "v1"
        e1["webpage_url"] = "https://www.youtube.com/watch?v=v1"
        e2 = dict(INFO)
        e2["id"] = "v2"
        e2["webpage_url"] = "https://www.youtube.com/watch?v=v2"
        pl = {"_type": "playlist", "title": "Playlist de prueba",
              "uploader": "Canal", "thumbnail": "https://i.ytimg.com/pl.jpg",
              "webpage_url": "https://www.youtube.com/playlist?list=PLxxx",
              "entries": [e1, e2]}
        r = analyzer._playlist(pl, "youtube", URL, {})
        self.assertTrue(r["es_playlist"])
        self.assertEqual(r["tipo"], "playlist")
        self.assertEqual(r["titulo"], "Playlist de prueba")
        self.assertEqual(r["autor"], "Canal")
        self.assertEqual(len(r["entradas"]), 2)
        for entrada in r["entradas"]:
            self.assertEqual(entrada["tipo"], "video")
            self.assertIn("calidades", entrada)

    def test_playlist_vacia(self):
        pl = {"_type": "playlist", "title": "Vacia", "entries": []}
        r = analyzer._playlist(pl, "youtube", URL, {})
        self.assertTrue(r["es_playlist"])
        self.assertEqual(r["entradas"], [])
        self.assertEqual(r["salteados"], [])

    def test_playlist_saltea_entry_que_falla(self):
        entry = dict(INFO)
        pl = {"_type": "playlist", "title": "PL", "entries": [entry]}
        with mock.patch.object(analyzer, "_resultado_de",
                               side_effect=Exception("boom")):
            r = analyzer._playlist(pl, "youtube", URL, {})
        self.assertEqual(r["entradas"], [])
        self.assertEqual(r["salteados"][0]["motivo"], "error_desconocido")

    def test_playlist_saltea_entry_con_error_miauki(self):
        entry = dict(INFO)
        pl = {"_type": "playlist", "title": "PL", "entries": [entry]}
        with mock.patch.object(analyzer, "_resultado_de",
                               side_effect=errors.ErrorMiauki("video_privado")):
            r = analyzer._playlist(pl, "youtube", URL, {})
        self.assertEqual(r["salteados"][0]["motivo"], "video_privado")

    def test_playlist_registra_entry_no_listada(self):
        # ignoreerrors de yt-dlp deja None en entries cuando no pudo listar.
        pl = {"_type": "playlist", "title": "PL",
              "entries": [dict(INFO), None]}
        r = analyzer._playlist(pl, "youtube", URL, {})
        self.assertEqual(len(r["entradas"]), 1)
        self.assertEqual(r["salteados"][0]["motivo"], "playlist_error_analisis")

    def test_playlist_entry_plana_trae_url_propia_y_miniatura(self):
        entry = {"id": "v1", "url": "https://www.youtube.com/watch?v=v1",
                 "title": "Video plano", "duration": 65,
                 "thumbnails": [{"url": "https://i.ytimg.com/vi/v1/hq.jpg"}]}
        pl = {"_type": "playlist", "title": "PL", "entries": [entry]}
        with mock.patch.object(analyzer.images, "data_uri_de",
                               return_value="data:image/jpeg;base64,AAA"):
            r = analyzer._playlist(pl, "youtube", URL, {})
        e = r["entradas"][0]
        self.assertEqual(e["url_canonica"],
                         "https://www.youtube.com/watch?v=v1")
        self.assertEqual(e["duracion"], 65)
        self.assertTrue(e["miniatura"].startswith("data:image/"))

    def test_playlist_con_entry_no_dict_se_ignora(self):
        pl = {"_type": "playlist", "title": "PL",
              "entries": [dict(INFO), None, "no-es-dict"]}
        r = analyzer._playlist(pl, "youtube", URL, {})
        self.assertEqual(len(r["entradas"]), 1)


class OpcionesYtdlp(unittest.TestCase):
    def test_opciones_basicas(self):
        o = analyzer._opciones_ajustes(AJUSTES)
        self.assertTrue(o["noplaylist"])
        self.assertTrue(o["quiet"])
        self.assertTrue(o["no_warnings"])
        self.assertEqual(o["socket_timeout"], 15)
        self.assertNotIn("cookiesfrombrowser", o)

    def test_cookies_del_navegador_elegido(self):
        o = analyzer._opciones_ajustes({"navegador_cookies": "chrome"})
        self.assertEqual(o["cookiesfrombrowser"], ("chrome",))

    def test_tiktok_usa_user_agent_de_navegador(self):
        """Sin esto TikTok responde "Unexpected response" (Fase 7, 0.3)."""
        o = analyzer._opciones_ajustes({}, "https://www.tiktok.com/@a/video/1")
        self.assertEqual(o["http_headers"]["User-Agent"], analyzer.UA_NAVEGADOR)
        self.assertTrue(analyzer.UA_NAVEGADOR.startswith("Mozilla/5.0"))

    def test_youtube_no_lleva_user_agent_forzado(self):
        o = analyzer._opciones_ajustes({}, "https://www.youtube.com/watch?v=jNQXAC9IVRw")
        self.assertNotIn("http_headers", o)


class Flujos(unittest.TestCase):
    def test_analizar_playlist(self):
        e1 = dict(INFO)
        e1["id"] = "v1"
        pl = {"_type": "playlist", "title": "Playlist de flujo",
              "webpage_url": "https://www.youtube.com/playlist?list=PLxxx",
              "entries": [e1]}
        with mock.patch.object(analyzer, "_extraer", return_value=pl):
            r = analyzer.analizar(URL, forzar=True)
        self.assertTrue(r["es_playlist"])
        self.assertEqual(len(r["entradas"]), 1)

    def setUp(self):
        analyzer._cache.clear()
        analyzer._hilo = None
        parche = mock.patch.object(analyzer.settings, "cargar",
                                   return_value=dict(AJUSTES))
        self.settings = parche.start()
        self.addCleanup(parche.stop)
        mini = mock.patch.object(analyzer.images, "data_uri_de",
                                 return_value=None)
        mini.start()
        self.addCleanup(mini.stop)

    def test_analizar_devuelve_estructura(self):
        with mock.patch.object(analyzer, "_extraer",
                               return_value=dict(INFO)) as ex:
            r = analyzer.analizar(URL)
        self.assertEqual(r["titulo"], "Video de prueba")
        self.assertTrue(ex.called)
        self.assertTrue(r["id_solicitud"])

    def test_link_de_portada_no_llega_a_ytdlp(self):
        with mock.patch.object(analyzer, "_extraer") as ex:
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar("https://www.tiktok.com/es/")
        self.assertEqual(ctx.exception.codigo, "no_es_video")
        self.assertFalse(ex.called)

    def test_error_de_ytdlp_se_mapea(self):
        with mock.patch.object(
                analyzer, "_extraer",
                side_effect=RuntimeError("You need to log in to access this content")):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(URL, forzar=True)
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")
        self.assertNotIn("bot", str(ctx.exception).lower())

    def test_foto_de_facebook_da_el_mensaje_especifico(self):
        foto = "https://www.facebook.com/photo/?fbid=1111696508036243"
        with mock.patch.object(
                analyzer, "_extraer",
                side_effect=RuntimeError(
                    "ERROR: Unsupported URL: " + foto)), \
             mock.patch.object(analyzer.images, "_og_image_de",
                               side_effect=analyzer.images._Falla(
                                   "no_es_video",
                                   "No encontré la imagen en esa página.")):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(foto, forzar=True)
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")
        self.assertIn("cookies", ctx.exception.mensaje.lower())

    def test_facebook_que_no_es_foto_usa_el_mensaje_generico(self):
        watch = "https://www.facebook.com/watch/?v=123"
        with mock.patch.object(
                analyzer, "_extraer",
                side_effect=RuntimeError("ERROR: Unsupported URL: " + watch)):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(watch, forzar=True)
        self.assertEqual(ctx.exception.mensaje,
                         errors.MENSAJES["sitio_no_soportado"])

    def test_error_con_url_no_guarda_query_en_el_log(self):
        exc = RuntimeError("fallo en https://x.com/a?token=SECRETO")
        with mock.patch.object(analyzer, "_extraer", side_effect=exc), \
             mock.patch.object(analyzer, "obtener_logger") as log:
            with self.assertRaises(ErrorMiauki):
                analyzer.analizar(URL, forzar=True)
        texto = str(log.return_value.warning.call_args)
        self.assertNotIn("token=SECRETO", texto)

    def test_instagram_perfil_publico(self):
        """Plan `plan.md`, paso 2.2: el perfil se abre como lista de posts."""
        e1 = {"id": "p1", "url": "https://www.instagram.com/p/p1/",
              "title": "Post 1", "thumbnails": []}
        e2 = {"id": "p2", "url": "https://www.instagram.com/p/p2/",
              "title": "Post 2", "thumbnails": []}
        pl = {"_type": "playlist", "title": "maki",
              "webpage_url": "https://www.instagram.com/maki/",
              "entries": [e1, e2]}
        with mock.patch.object(analyzer, "_extraer", return_value=pl):
            r = analyzer.analizar("https://www.instagram.com/maki/", forzar=True)
        self.assertTrue(r["es_playlist"])
        self.assertEqual(len(r["entradas"]), 2)
        for entrada in r["entradas"]:
            self.assertIn(entrada["tipo"], ("video", "imagen"))

    def test_instagram_perfil_requiere_sesion_propaga_error(self):
        with mock.patch.object(
                analyzer, "_extraer",
                side_effect=RuntimeError("Instagram sent an empty media response")):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar("https://www.instagram.com/maki/", forzar=True)
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")
        self.assertIn("Ajustes", ctx.exception.mensaje)
        self.assertIn("Usar el inicio de sesión de tu navegador",
                      ctx.exception.mensaje)

    def test_instagram_perfil_respeta_max_playlist(self):
        pl = {"_type": "playlist", "title": "maki",
              "webpage_url": "https://www.instagram.com/maki/",
              "entries": [{"id": "p%d" % i, "url": "https://www.instagram.com/p/%d/" % i}
                          for i in range(601)]}
        with mock.patch.object(analyzer, "_extraer", return_value=pl):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar("https://www.instagram.com/maki/", forzar=True)
        self.assertEqual(ctx.exception.codigo, "playlist_muy_larga")

    def test_instagram_perfil_playlist_largo_bloques(self):
        """350 entra bajo el tope de 600: la cola la arma en 2 bloques de 200."""
        pl = {"_type": "playlist", "title": "maki",
              "webpage_url": "https://www.instagram.com/maki/",
              "entries": [{"id": "p%d" % i, "url": "https://www.instagram.com/p/%d/" % i}
                          for i in range(350)]}
        with mock.patch.object(analyzer, "_extraer", return_value=pl):
            r = analyzer.analizar("https://www.instagram.com/maki/", forzar=True)
        self.assertEqual(len(r["entradas"]), 350)
        # 350 pasa el tope y entra en más de un bloque de la cola (TAM_BLOQUE).
        self.assertLessEqual(len(r["entradas"]), analyzer.validacion.MAX_PLAYLIST)
        self.assertGreater(len(r["entradas"]), analyzer.validacion.TAM_BLOQUE)

    def test_perfil_instagram_pide_listado_plano(self):
        o = analyzer._opciones_ajustes({}, "https://www.instagram.com/maki/")
        self.assertEqual(o["extract_flat"], "in_playlist")
        self.assertTrue(o["ignoreerrors"])
        self.assertEqual(o["playlistend"], 601)
        # Un post suelto no se trata como lista.
        o2 = analyzer._opciones_ajustes({}, "https://www.instagram.com/p/abc/")
        self.assertNotIn("extract_flat", o2)

    def test_motor_sin_datos_da_error_amable(self):
        """ignoreerrors deja None: no puede salir una tarjeta vacía."""
        with mock.patch.object(analyzer, "_extraer", return_value=None):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar("https://www.instagram.com/maki/", forzar=True)
        self.assertEqual(ctx.exception.codigo, "error_desconocido")

    def test_un_analisis_a_la_vez(self):
        lento = threading.Event()

        def lento_asi(*a, **k):
            lento.wait(2)
            return dict(INFO)

        with mock.patch.object(analyzer, "_extraer", side_effect=lento_asi):
            h1 = threading.Thread(target=analyzer.analizar, args=(URL,))
            h1.start()
            time.sleep(0.15)
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(URL)
            self.assertEqual(ctx.exception.codigo, "analisis_en_curso")
            lento.set()
            h1.join(3)

    def test_timeout_amable_y_huorfano_limitado(self):
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=lambda *a, **k: (time.sleep(0.8),
                                                            dict(INFO))[1]):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(URL, tiempo_max=0.1)
            self.assertEqual(ctx.exception.codigo, "tiempo_agotado")
            # el hilo viejo sigue: la siguiente llamada se rechaza (límite A3)
            with self.assertRaises(ErrorMiauki) as ctx2:
                analyzer.analizar(URL, forzar=True)
            self.assertEqual(ctx2.exception.codigo, "analisis_en_curso")
            time.sleep(0.9)

    def test_cache_segunda_llamada_es_rapida_y_forzar_reanaliza(self):
        def lento(*a, **k):
            time.sleep(0.5)
            return dict(INFO)

        with mock.patch.object(analyzer, "_extraer", side_effect=lento) as ex:
            t0 = time.monotonic()
            analyzer.analizar(URL, tiempo_max=5)
            lenta = time.monotonic() - t0
            t1 = time.monotonic()
            r2 = analyzer.analizar(URL, tiempo_max=5)
            rapida = time.monotonic() - t1
            self.assertEqual(ex.call_count, 1)
            self.assertEqual(r2["titulo"], "Video de prueba")
            self.assertLess(rapida, 0.3)
            self.assertGreaterEqual(lenta, 0.5)
            analyzer.analizar(URL, forzar=True, tiempo_max=5)
            self.assertEqual(ex.call_count, 2)

    def test_los_errores_no_se_cachean(self):
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Video unavailable")) as ex:
            for _ in range(2):
                with self.assertRaises(ErrorMiauki):
                    analyzer.analizar(URL, forzar=False)
        self.assertEqual(ex.call_count, 2)

    def test_cache_toma_como_clave_url_y_ajustes(self):
        with mock.patch.object(analyzer, "_extraer",
                               return_value=dict(INFO)) as ex:
            analyzer.analizar(URL)
            self.settings.return_value = {"navegador_cookies": "chrome",
                                          "idioma_subs": "es"}
            analyzer.analizar(URL)
            self.assertEqual(ex.call_count, 2)

    def test_cache_tope_20_entradas(self):
        with mock.patch.object(analyzer, "_extraer",
                               return_value=dict(INFO)):
            for i in range(25):
                analyzer.analizar("https://www.youtube.com/watch?v=v%02d" % i)
        self.assertLessEqual(len(analyzer._cache), 20)


URL_X = "https://x.com/u/status/1234567890123456789/photo/1"
FOTO_A = "https://pbs.twimg.com/media/a.jpg?name=4096x4096"
FOTO_B = "https://pbs.twimg.com/media/b.jpg?name=4096x4096"
URI_A = "data:image/jpeg;base64,XXA"
URI_B = "data:image/jpeg;base64,XXB"
DATOS_VIAS = {"imagenes": [FOTO_A],
              "titulo": "Pepe - hola", "autor": "Pepe", "via": "graphql",
              "sitio": "x"}


class ViasXEnAnalyzer(unittest.TestCase):
    """§5: si yt-dlp no analiza fotos de X, mandan las vías propias."""

    def setUp(self):
        analyzer._cache.clear()
        analyzer._hilo = None
        parche = mock.patch.object(analyzer.settings, "cargar",
                                   return_value=dict(AJUSTES))
        parche.start()
        self.addCleanup(parche.stop)
        mini = mock.patch.object(analyzer.images, "data_uri_de",
                                 side_effect=lambda u: URI_A if u == FOTO_A
                                 else URI_B if u == FOTO_B else None)
        mini.start()
        self.addCleanup(mini.stop)

    def test_x_falla_ytdlp_y_las_vias_salvan(self):
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Unsupported URL")), \
             mock.patch.object(analyzer.images, "imagenes_de",
                               return_value=dict(DATOS_VIAS)) as vias:
            r = analyzer.analizar(URL_X, forzar=True)
        self.assertEqual(r["tipo"], "imagen")
        self.assertEqual(r["tipos"], ["imagen"])
        self.assertEqual(r["sitio"], "x")
        self.assertEqual(r["titulo"], "Pepe - hola")
        # La UI solo puede mostrar data:image/ (CSP img-src 'self' data:):
        # las vías devuelven URLs y el análisis las convierte antes de salir.
        self.assertEqual(r["imagenes"], [URI_A])
        # La URL real viaja aparte para encolar la descarga (3d.13).
        self.assertEqual(r["imagenes_urls"], [FOTO_A])
        self.assertEqual(r["miniatura"], URI_A)
        self.assertEqual(r["calidades"], [])
        self.assertTrue(r["id_solicitud"])
        vias.assert_called_once()

    def test_foto_que_no_se_puede_bajar_se_descarta(self):
        datos = dict(DATOS_VIAS, imagenes=[FOTO_A, FOTO_B])
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Unsupported URL")), \
             mock.patch.object(analyzer.images, "imagenes_de",
                               return_value=datos), \
             mock.patch.object(analyzer.images, "data_uri_de",
                               side_effect=lambda u: None if u == FOTO_A
                               else URI_B):
            r = analyzer.analizar(URL_X, forzar=True)
        self.assertEqual(r["imagenes"], [URI_B])
        self.assertEqual(r["imagenes_urls"], [FOTO_B])
        self.assertEqual(r["miniatura"], URI_B)

    def test_si_las_vias_piden_sesion_ese_es_el_error(self):
        """Fase 9 B2: el mensaje útil es "falta sesión", no el de yt-dlp."""
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Unsupported URL")), \
             mock.patch.object(analyzer.images, "imagenes_de",
                               side_effect=ErrorMiauki("requiere_sesion")):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(URL_X, forzar=True)
        self.assertEqual(ctx.exception.codigo, "requiere_sesion")

    def test_si_las_vias_fallan_por_otra_cosa_da_el_error_original(self):
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Unsupported URL")), \
             mock.patch.object(analyzer.images, "imagenes_de",
                               side_effect=RuntimeError("via rota")):
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(URL_X, forzar=True)
        self.assertEqual(ctx.exception.codigo, "sitio_no_soportado")

    def test_otro_sitio_no_usa_las_vias(self):
        with mock.patch.object(analyzer, "_extraer",
                               side_effect=RuntimeError("Video unavailable")), \
             mock.patch.object(analyzer.images, "imagenes_de") as vias:
            with self.assertRaises(ErrorMiauki) as ctx:
                analyzer.analizar(URL, forzar=True)
        self.assertEqual(ctx.exception.codigo, "video_eliminado")
        self.assertFalse(vias.called)

    def test_exito_de_ytdlp_en_x_no_toca_las_vias(self):
        with mock.patch.object(analyzer, "_extraer",
                               return_value=dict(INFO)), \
             mock.patch.object(analyzer.images, "imagenes_de") as vias:
            r = analyzer.analizar(URL_X, forzar=True)
        self.assertEqual(r["tipo"], "video")
        self.assertFalse(vias.called)


class MaximaCompatibilidad(unittest.TestCase):
    """B1: la lista completa de calidades (decisión Maki 07/11: sin tope)."""

    def setUp(self):
        mini = mock.patch.object(analyzer.images, "data_uri_de",
                                 return_value=None)
        mini.start()
        self.addCleanup(mini.stop)

    def _info_multicodec(self):
        return _info(formats=[
            {"format_id": "401", "height": 2160, "vcodec": "av01.0.12M.08",
             "acodec": "none", "tbr": 20000, "filesize": 40000000, "ext": "mp4"},
            {"format_id": "313", "height": 2160, "vcodec": "vp9",
             "acodec": "none", "tbr": 18000, "filesize": 38000000, "ext": "webm"},
            {"format_id": "299", "height": 1080, "vcodec": "avc1.64002a",
             "acodec": "none", "tbr": 4500, "filesize": 9500000, "ext": "mp4"},
            {"format_id": "303", "height": 1080, "vcodec": "vp9",
             "acodec": "none", "tbr": 4000, "filesize": 9000000, "ext": "webm"},
            {"format_id": "22", "height": 720, "vcodec": "avc1.64001F",
             "acodec": "mp4a.40.2", "tbr": 2500, "filesize": 7000000,
             "ext": "mp4"},
            {"format_id": "251", "height": None, "vcodec": "none",
             "acodec": "opus", "tbr": 160, "filesize": 200000, "ext": "webm"},
            {"format_id": "140", "height": None, "vcodec": "none",
             "acodec": "mp4a.40.2", "tbr": 128, "filesize": 180000,
             "ext": "m4a"},
        ])

    def test_la_lista_siempre_todas_las_alturas(self):
        """Decisión Maki (07/11): se listan TODAS las alturas, sin tope."""
        r = analyzer._resultado_de(self._info_multicodec(), "youtube", URL)
        alturas = [o["resolucion"] for o in r["calidades"]]
        self.assertEqual(alturas, [2160, 1080, 720])
        self.assertIn(2160, alturas)

    def test_cada_altura_entrege_su_formato_y_codec(self):
        r = analyzer._resultado_de(self._info_multicodec(), "youtube", URL)
        opciones = {o["resolucion"]: o for o in r["calidades"]}
        self.assertEqual(opciones[2160]["contenedor"], "mkv")
        self.assertEqual(opciones[2160]["codec"], "av1")
        self.assertEqual(opciones[1080]["contenedor"], "mp4")
        self.assertEqual(opciones[1080]["codec"], "h264")
        self.assertEqual(opciones[720]["contenedor"], "mp4")
        self.assertEqual(opciones[720]["codec"], "h264")

    def test_el_mejor_es_la_altura_maxima(self):
        r = analyzer._resultado_de(self._info_multicodec(), "youtube", URL)
        mejor = r["calidades"][0]
        self.assertEqual(mejor["recomendada"], "La mejor")
        self.assertEqual(mejor["etiqueta"], "2160p")

    def test_ofrece_2160_con_av1_o_vp9(self):
        r = analyzer._resultado_de(self._info_multicodec(), "youtube", URL)
        primero = r["calidades"][0]
        self.assertEqual(primero["resolucion"], 2160)
        self.assertIn(primero["codec"], ("av1", "vp9"))

    def test_dos_contenedores_en_la_misma_altura(self):
        """Paso 2: la misma altura con mp4 (H.264) y mkv (VP9) = dos opciones."""
        info = _info(formats=[
            {"format_id": "22", "height": 720, "vcodec": "avc1.64001F",
             "acodec": "mp4a.40.2", "tbr": 2500, "filesize": 7000000, "ext": "mp4"},
            {"format_id": "43", "height": 720, "vcodec": "vp09.00.10.08",
             "acodec": "opus", "tbr": 2800, "filesize": 8000000, "ext": "webm"},
        ])
        r = analyzer._resultado_de(info, "youtube", URL)
        del_720 = [c for c in r["calidades"] if c["etiqueta"] == "720p"]
        self.assertEqual(len(del_720), 2)
        self.assertEqual(del_720[0]["contenedor"], "mp4")
        self.assertEqual(del_720[0]["codec"], "h264")
        self.assertEqual(del_720[0]["peso_bytes"], 7000000)
        self.assertEqual(del_720[0]["recomendada"], "La mejor")
        self.assertEqual(del_720[1]["contenedor"], "mkv")
        self.assertEqual(del_720[1]["codec"], "vp9")
        self.assertEqual(del_720[1]["peso_bytes"], 8000000)

    def test_sin_h264_en_ningun_lado_no_deja_la_lista_vacia(self):
        solo_av1 = _info(formats=[
            {"format_id": "401", "height": 2160, "vcodec": "av01.0.12M.08",
             "acodec": "none", "tbr": 20000, "filesize": 1000, "ext": "mp4"},
            {"format_id": "399", "height": 1080, "vcodec": "av01.0.08M.08",
             "acodec": "none", "tbr": 4000, "filesize": 500, "ext": "mp4"},
            {"format_id": "251", "height": None, "vcodec": "none",
             "acodec": "opus", "tbr": 160, "filesize": 50, "ext": "webm"},
        ])
        r = analyzer._resultado_de(solo_av1, "youtube", URL)
        self.assertEqual([o["resolucion"] for o in r["calidades"]], [2160, 1080])
        self.assertEqual(r["calidades"][0]["codec"], "av1")

    def test_si_solo_hay_mas_de_1080_baja_a_la_mas_chica(self):
        solo_grande = _info(formats=[
            {"format_id": "1", "height": 2160, "vcodec": "avc1.640033",
             "acodec": "none", "tbr": 12000, "filesize": 3000000, "ext": "mp4"},
            {"format_id": "2", "height": 1440, "vcodec": "avc1.640032",
             "acodec": "none", "tbr": 8000, "filesize": 2000000, "ext": "mp4"},
            {"format_id": "3", "height": None, "vcodec": "none",
             "acodec": "mp4a.40.2", "tbr": 128, "filesize": 100, "ext": "m4a"},
        ])
        r = analyzer._resultado_de(solo_grande, "youtube", URL)
        self.assertEqual([o["resolucion"] for o in r["calidades"]], [2160, 1440])

    def test_vertical_1080_si_entra(self):
        vertical = _info(formats=[
            {"format_id": "v", "height": 1920, "width": 1080,
             "vcodec": "avc1.640028", "acodec": "none", "tbr": 3000,
             "filesize": 800000, "ext": "mp4"},
            {"format_id": "h", "height": 3840, "width": 2160,
             "vcodec": "avc1.640033", "acodec": "none", "tbr": 12000,
             "filesize": 3000000, "ext": "mp4"},
        ])
        r = analyzer._resultado_de(vertical, "tiktok", URL)
        self.assertEqual([o["resolucion"] for o in r["calidades"]], [2160, 1080])
        op = {o["resolucion"]: o for o in r["calidades"]}[1080]
        self.assertIn("width<=1080", op["selector"])


class ReintentoVerificacionBot(unittest.TestCase):
    """Tanda 20/11/2026, paso 5: solo el aviso anti-bot se reintenta."""

    def _extraer(self, fallas):
        intentos = []

        class YdlFalso:
            def __init__(self, opciones):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                intentos.append(url)
                if len(intentos) <= fallas:
                    raise RuntimeError("Sign in to confirm you're not a bot")
                return {"id": "abc123", "title": "ok"}

            def sanitize_info(self, info):
                return info

        class YtFalso:
            YoutubeDL = YdlFalso

        with mock.patch.object(analyzer.motor, "ytdlp", return_value=YtFalso), \
                mock.patch.object(analyzer, "_opciones_ajustes", return_value={}), \
                mock.patch.object(analyzer, "ESPERAS_ANALISIS", (0,)), \
                mock.patch.object(errors, "ESPERA_BOT", 0):
            info = analyzer._extraer(URL, {})
        return info, intentos

    def test_reintenta_dos_veces_y_termina_bien(self):
        info, intentos = self._extraer(fallas=2)
        self.assertEqual(intentos, [URL, URL, URL])
        self.assertEqual(info["title"], "ok")

    def test_espera_paciente_tras_los_dos_reintentos(self):
        """Paso 3: después de los 2 reintentos cortos, espera 5 s y prueba otra vez."""
        esperas = []

        class YdlFalso:
            def __init__(self, opciones):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                raise RuntimeError("Sign in to confirm you're not a bot")

            def sanitize_info(self, info):
                return info

        class YtFalso:
            YoutubeDL = YdlFalso

        with mock.patch.object(analyzer.motor, "ytdlp", return_value=YtFalso), \
                mock.patch.object(analyzer, "_opciones_ajustes", return_value={}), \
                mock.patch.object(analyzer, "ESPERAS_ANALISIS", (5.0,)), \
                mock.patch.object(errors, "ESPERA_BOT", 3.0), \
                mock.patch.object(analyzer.time, "sleep", side_effect=esperas.append):
            with self.assertRaises(RuntimeError):
                analyzer._extraer(URL, {})
        self.assertEqual(esperas, [3.0, 3.0, 5.0])

    def test_si_sigue_el_aviso_informa_el_error(self):
        with self.assertRaises(RuntimeError):
            self._extraer(fallas=99)

    def test_otro_error_no_se_reintenta(self):
        # Ajustes 21/11: el eliminado pasajero SÍ se reintenta; este test usa
        # un error real distinto (sitio no soportado) que no debe reintentarse.
        intentos = []

        class YdlFalso:
            def __init__(self, opciones):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                intentos.append(url)
                raise RuntimeError("ERROR: Unsupported URL: https://ejemplo.com/xx")

            def sanitize_info(self, info):
                return info

        class YtFalso:
            YoutubeDL = YdlFalso

        with mock.patch.object(analyzer.motor, "ytdlp", return_value=YtFalso), \
                mock.patch.object(analyzer, "_opciones_ajustes", return_value={}):
            with self.assertRaises(RuntimeError):
                analyzer._extraer(URL, {})
        self.assertEqual(len(intentos), 1)

    def test_eliminado_pasajero_se_reintenta_una_vez(self):
        intentos = []

        class YdlFalso:
            def __init__(self, opciones):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                intentos.append(url)
                if len(intentos) == 1:
                    raise RuntimeError(
                        "Video unavailable. This video has been removed by "
                        "the uploader")
                return {"title": "ok", "formats": [], "entries": []}

            def sanitize_info(self, info):
                return info

        class YtFalso:
            YoutubeDL = YdlFalso

        with mock.patch.object(analyzer.motor, "ytdlp", return_value=YtFalso), \
                mock.patch.object(analyzer, "_opciones_ajustes", return_value={}):
            info = analyzer._extraer(URL, {})
        self.assertEqual(len(intentos), 2)
        self.assertEqual(info["title"], "ok")


    def test_error_que_ytdlp_ignora_se_recupera(self):
        """ignoreerrors devuelve None: el error real no se pierde."""
        intentos = []

        class YdlFalso:
            def __init__(self, opciones):
                self._opciones = opciones

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                intentos.append(url)
                self._opciones["logger"].error(
                    "ERROR: [youtube] abc: Sign in to confirm you're not a bot")
                return None

            def sanitize_info(self, info):
                return info

        class YtFalso:
            YoutubeDL = YdlFalso

        with mock.patch.object(analyzer.motor, "ytdlp", return_value=YtFalso), \
                mock.patch.object(analyzer, "_opciones_ajustes", return_value={}), \
                mock.patch.object(analyzer, "ESPERAS_ANALISIS", (0,)), \
                mock.patch.object(errors, "ESPERA_BOT", 0):
            with self.assertRaises(RuntimeError) as ctx:
                analyzer._extraer(URL, {})
        self.assertEqual(errors.codigo_de(str(ctx.exception)),
                         "youtube_verificacion_bot")
        # el intento original + 2 reintentos + 1 espera paciente (paso 3)
        self.assertEqual(len(intentos), 4)


class RotacionClientesYoutube(unittest.TestCase):
    """Tanda 22/11/2026, paso 2: cada reintento imita otra app de YouTube."""

    def test_rota_clientes_tras_el_bloqueo(self):
        vistos = []

        class YdlFalso:
            def __init__(self, opciones):
                cliente = (opciones.get("extractor_args") or {}).get(
                    "youtube", {}).get("player_client")
                vistos.append(cliente)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def extract_info(self, url, download=False):
                if len(vistos) <= 2:
                    raise RuntimeError("Sign in to confirm you're not a bot")
                return {"title": "ok"}

            def sanitize_info(self, info):
                return info

        class YtFalso:
            YoutubeDL = YdlFalso

        with mock.patch.object(analyzer.motor, "ytdlp", return_value=YtFalso), \
                mock.patch.object(analyzer, "_opciones_ajustes", return_value={}), \
                mock.patch.object(errors, "ESPERA_BOT", 0):
            info = analyzer._extraer(URL, {})
        self.assertEqual(info["title"], "ok")
        self.assertEqual(vistos, [None, ["android"], ["tv"]])


class PlaylistCalidad(unittest.TestCase):
    """Tanda 20/11 #2: decisión de calidades en playlists (híbrido)."""

    def _pl(self, entradas, sondeo):
        info = {"_type": "playlist", "title": "Lista",
                "webpage_url": "https://youtube.com/playlist?list=abc",
                "entries": entradas}
        with mock.patch.object(analyzer, "_sondear_calidades_playlist",
                               return_value=sondeo):
            return analyzer._playlist(
                info, "youtube",
                "https://youtube.com/playlist?list=abc", {})

    def _entrada(self, i):
        return {"id": "v%d" % i, "title": "Video %d" % i,
                "url": "https://www.youtube.com/watch?v=v%d" % i}

    def test_uniforme_8k_ofrece_4320_como_maxima(self):
        entradas = [self._entrada(i) for i in range(5)]
        alturas = {e["url"]: 4320 for e in entradas}
        sondeo = {"alturas": alturas, "incompleto": False}
        r = self._pl(entradas, sondeo)
        self.assertEqual(r["modo_calidad"], "uniforme")
        self.assertEqual(r["calidad_defecto"], "4320")
        valores = [c["valor"] for c in r["calidades"]]
        self.assertEqual(valores[0], "4320")
        self.assertIn("2160", valores)
        self.assertIn("musica", valores)
        self.assertEqual(len(r["entradas"]), 5)
        self.assertEqual(r["salteados"], [])

    def test_uniforme_2k_ofrece_1440_como_maxima(self):
        entradas = [self._entrada(i) for i in range(4)]
        alturas = {e["url"]: 1440 for e in entradas}
        sondeo = {"alturas": alturas, "incompleto": False}
        r = self._pl(entradas, sondeo)
        self.assertEqual(r["calidad_defecto"], "1440")
        self.assertEqual(r["calidades"][0]["valor"], "1440")
        self.assertNotIn("4320", [c["valor"] for c in r["calidades"]])

    def test_mixta_ofrece_calidad_maxima_y_no_salte__por_calidad(self):
        entradas = [self._entrada(i) for i in range(5)]
        alturas = {entradas[0]["url"]: 2160, entradas[1]["url"]: 1080,
                   entradas[2]["url"]: 1080, entradas[3]["url"]: 720,
                   entradas[4]["url"]: 480}
        sondeo = {"alturas": alturas, "incompleto": False}
        r = self._pl(entradas, sondeo)
        self.assertEqual(r["modo_calidad"], "mixta")
        # "Calidad Máxima" (mejor) es la opción por defecto y la primera.
        self.assertEqual(r["calidad_defecto"], "mejor")
        self.assertEqual([c["valor"] for c in r["calidades"]],
                         ["mejor", "1080", "720", "480", "musica"])
        # Todos los videos se encolan (cada uno baja en su mejor calidad);
        # nada se saltea por baja calidad (decisión de Maki, 20/11 #2).
        self.assertEqual(len(r["entradas"]), 5)
        self.assertEqual(r["salteados"], [])

    def test_fallback_por_sondeo_incompleto_conserva_mejor(self):
        entradas = [self._entrada(i) for i in range(3)]
        sondeo = {"alturas": {}, "incompleto": True}
        r = self._pl(entradas, sondeo)
        self.assertEqual(r["modo_calidad"], "fallback")
        self.assertEqual(r["calidad_defecto"], "mejor")
        self.assertEqual(r["calidades"][0]["valor"], "mejor")
        self.assertEqual(len(r["entradas"]), 3)
        self.assertEqual(r["salteados"], [])

    def test_corte_temprano_por_mezcla_no_exige_sondeo_completo(self):
        # Si al sondear ya aparecen alturas distintas, se corta temprano y
        # la lista se trata como mixta aunque no se haya sondeado todo.
        entradas = [self._entrada(i) for i in range(10)]
        alturas = {entradas[0]["url"]: 4320, entradas[1]["url"]: 1080}
        sondeo = {"alturas": alturas, "incompleto": False}
        r = self._pl(entradas, sondeo)
        self.assertEqual(r["modo_calidad"], "mixta")
        self.assertEqual(r["calidad_defecto"], "mejor")
        self.assertEqual(r["calidades"][0]["valor"], "mejor")

    def test_uniforme_estimado_por_muestra_amplia_con_advertencia(self):
        # Sondeo incompleto pero muestra amplia (>=50%) y toda coincidente:
        # se muestra la calidad uniforme con advertencia honesta.
        entradas = [self._entrada(i) for i in range(10)]
        alturas = {entradas[i]["url"]: 4320 for i in range(6)}
        sondeo = {"alturas": alturas, "incompleto": True}
        r = self._pl(entradas, sondeo)
        self.assertEqual(r["modo_calidad"], "uniforme")
        self.assertEqual(r["calidad_defecto"], "4320")
        self.assertEqual(r["calidades"][0]["valor"], "4320")
        self.assertTrue(any("muestra" in a for a in r["advertencias"]))

    def test_fallback_cuando_muestra_chica_incompleta(self):
        # Sondeo incompleto con muestra chica (<50%): no se afirma uniformidad.
        entradas = [self._entrada(i) for i in range(10)]
        alturas = {entradas[0]["url"]: 4320}
        sondeo = {"alturas": alturas, "incompleto": True}
        r = self._pl(entradas, sondeo)
        self.assertEqual(r["modo_calidad"], "fallback")
        self.assertEqual(r["calidad_defecto"], "mejor")


if __name__ == "__main__":
    unittest.main()

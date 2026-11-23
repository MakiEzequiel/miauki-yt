# -*- coding: utf-8 -*-
"""Tests de errors.py: códigos, mensajes amables y mapeo de yt-dlp (A4)."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import errors  # noqa: E402


class Codigos(unittest.TestCase):
    def test_los_12_codigos_tienen_mensaje(self):
        esperados = [
            "link_invalido", "sitio_no_soportado", "video_privado",
            "video_eliminado", "requiere_sesion", "restriccion_edad",
            "no_disponible_pais", "sin_internet", "tiempo_agotado",
            "sin_subtitulos", "calidad_no_disponible", "error_desconocido",
        ]
        for c in esperados:
            self.assertIn(c, errors.MENSAJES, f"falta el código {c}")
            self.assertTrue(errors.MENSAJES[c].strip())

    def test_codigos_de_deteccion_de_sitios(self):
        self.assertIn("lista_reproduccion", errors.MENSAJES)
        self.assertIn("no_es_video", errors.MENSAJES)
        self.assertEqual(errors.MENSAJES["no_es_video"], "Ese link no es de un video.")

    def test_codigo_de_operacion_a3(self):
        self.assertIn("analisis_en_curso", errors.MENSAJES)
    def test_mensajes_sin_jerga_tecnica(self):
        prohibidas = ["http", "yt-dlp", "extractor", "traceback", "exception"]
        for m in errors.MENSAJES.values():
            for p in prohibidas:
                self.assertNotIn(p, m.lower(), f"mensaje con jerga: {m}")

    def test_requiere_sesion_menciona_ajustes_cookies(self):
        # Decisión de Maki (Fase 3B, 15/10/2026): los mensajes de
        # "requiere iniciar sesión" deben mencionar Ajustes → Cookies.
        # Fase 8, 0.1: el ajuste se llama ahora "Usar el inicio de sesión de tu
        # navegador"; el mensaje tiene que decir lo mismo que la pantalla.
        m = errors.MENSAJES["requiere_sesion"]
        self.assertIn("Ajustes", m)
        self.assertIn("Usar el inicio de sesión de tu navegador", m)


    def test_requiere_sesion_nombra_el_ajuste_exacto(self):
        """Plan `plan.md`, paso 2.3: el nombre del ajuste va tal cual."""
        self.assertIn("Usar el inicio de sesión de tu navegador",
                      errors.MENSAJES["requiere_sesion"])


class JavaScriptParaYouTube(unittest.TestCase):
    """0.6: falta el intérprete de JavaScript (ver docs/JS_YOUTUBE.md)."""

    def test_el_codigo_existe_y_no_usa_jerga(self):
        self.assertIn("motor_sin_js", errors.MENSAJES)
        m = errors.MENSAJES["motor_sin_js"]
        self.assertIn("Buscar actualización", m)
        for prohibida in ("javascript", "runtime", "deno", "node", "ejs"):
            self.assertNotIn(prohibida, m.lower())

    def test_los_mensajes_reales_caen_en_ese_codigo(self):
        casos = [
            "WARNING: [youtube] No supported JavaScript runtime could be found. "
            "Only deno is enabled by default",
            "Signature solving failed: Some formats may be missing. Ensure you "
            "have a supported JavaScript runtime and challenge solver script "
            "distribution installed.",
            "n challenge solving failed: Some formats may be missing.",
        ]
        for texto in casos:
            with self.subTest(texto=texto[:40]):
                self.assertEqual(errors.codigo_de(texto), "motor_sin_js")

    def test_la_interfaz_muestra_el_boton_buscar_actualizacion(self):
        js = (Path(__file__).resolve().parent.parent / "miauki" / "ui" / "js"
              / "app.js").read_text(encoding="utf-8")
        self.assertIn('codigo !== "motor_viejo" && codigo !== "motor_sin_js"', js)


class MapeoYtDlp(unittest.TestCase):
    def test_mensajes_reales_de_ytdlp(self):
        casos = [
            ("ERROR: [youtube] The video is private", "video_privado"),
            ("ERROR: You need to log in to access this content", "requiere_sesion"),
            ("ERROR: Video unavailable", "video_eliminado"),
            ("ERROR: This video is not available in your country", "no_disponible_pais"),
            ("ERROR: Requested format is not available", "calidad_no_disponible"),
            ("ERROR: urlopen error timed out", "tiempo_agotado"),
            ("ERROR: unable to download webpage: [Errno 11001] getaddrinfo failed",
             "sin_internet"),
            ("ERROR: Unsupported URL: https://ejemplo.com/xx", "sitio_no_soportado"),
            ("ERROR: The uploader has not made this video available in your country",
             "no_disponible_pais"),
            ("Sign in to confirm your age", "restriccion_edad"),
            ("This video is unavailable", "video_eliminado"),
            # Reales de la corrida B9:
            ("ERROR: [twitter] 2110183275461513256: Media #1 is not a video",
             "no_es_video"),
            ("ERROR: Unsupported URL: "
             "https://www.facebook.com/photo/?fbid=1111696508036243",
             "sitio_no_soportado"),
            # Facebook sin sesión: el extractor no puede leer los datos (P0.5)
            ("ERROR: [facebook] Cannot parse data", "requiere_sesion"),
            # Fase 9, B2: cookies cifradas (Edge en esta PC, yt-dlp 10927) y
            # navegador sin perfil. Reales de la corrida del 22/10/2026.
            ("ERROR: Failed to decrypt with DPAPI.", "cookies_bloqueadas"),
            ("ERROR: could not find edge cookies database in 'C:\\...'",
             "cookies_no_encontradas"),
            # Fase 9, B2b: archivo de cookies con formato inválido (mensaje real
            # del motor, FAQ de yt-dlp).
            ("ERROR: MyCookies.txt does not look like a Netscape format cookies file",
             "cookies_archivo_invalido"),
            # Instagram sin sesión (real, corrida C2 del 23/10/2026).
            ("ERROR: [Instagram] CqLM8XDLNKI: Instagram sent an empty media response.",
             "requiere_sesion"),
            # Auditoría 23/11: estados HTTP reales. Antes caían en
            # "sin_internet" por el fragmento genérico "unable to download webpage".
            ("ERROR: Unable to download webpage: HTTP Error 404: Not Found",
             "video_eliminado"),
            ("ERROR: [generic] HTTP Error 410: Gone", "video_eliminado"),
            ("ERROR: HTTP Error 403: Forbidden", "bloqueo_sitio"),
            ("ERROR: HTTP Error 429: Too Many Requests", "bloqueo_sitio"),
            ("ERROR: HTTP Error 401: Unauthorized", "requiere_sesion"),
        ]
        for texto, codigo in casos:
            self.assertEqual(errors.codigo_de(texto), codigo, texto)

    def test_desconocido_da_error_desconocido(self):
        self.assertEqual(errors.codigo_de("algo raro que nadie vio venir"),
                         "error_desconocido")

    def test_bloqueo_sitio_tiene_mensaje(self):
        self.assertIn("bloqueo_sitio", errors.MENSAJES)
        self.assertTrue(errors.MENSAJES["bloqueo_sitio"].strip())
        self.assertNotEqual(errors.codigo_de("HTTP Error 403: Forbidden"),
                            "sin_internet")

    def test_case_insensitive(self):
        self.assertEqual(errors.codigo_de("PRIVATE VIDEO"), "video_privado")

    def test_falsos_eliminados_mapean_a_su_causa_real(self):
        # Ajustes 21/11: frases que antes caían en "video_eliminado" o en
        # "error_desconocido" y que son bloqueos pasajeros o pedidos de
        # sesión, no videos borrados.
        casos = [
            ("ERROR: Video unavailable. This video has been removed by the uploader",
             "video_eliminado"),
            ("ERROR: This video has been removed for violating YouTube's policy",
             "video_eliminado"),
            ("This video is available to this channel's members only",
             "requiere_sesion"),
            ("Sign in to watch this video", "requiere_sesion"),
            ("ERROR: Please complete the captcha", "youtube_verificacion_bot"),
            ("ERROR: Unusual traffic detected", "youtube_verificacion_bot"),
            ("ERROR: reCAPTCHA verification failed", "youtube_verificacion_bot"),
            ("ERROR: Page unavailable. Try again later", "tiempo_agotado"),
        ]
        for texto, codigo in casos:
            with self.subTest(texto=texto[:60]):
                self.assertEqual(errors.codigo_de(texto), codigo)


class InstagramStories(unittest.TestCase):
    """Plan `plan.md`, paso 1.1: los dos errores reales de InstagramStoryIE."""

    def test_historia_que_pide_sesion(self):
        for texto in [
            "ERROR: [instagram:story] x: You need to log in to access this content.",
            "You need to log in to access this content",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(errors.codigo_de(texto), "requiere_sesion")

    def test_historia_no_disponible(self):
        for texto in [
            "ERROR: [instagram:story] 3570766765028588805: This content is unreachable",
            "This content is unreachable",
        ]:
            with self.subTest(texto=texto):
                self.assertEqual(errors.codigo_de(texto), "video_eliminado")


class Excepcion(unittest.TestCase):
    def test_lleva_codigo_y_mensaje_amable(self):
        e = errors.ErrorMiauki("video_privado")
        self.assertEqual(e.codigo, "video_privado")
        self.assertEqual(str(e), errors.MENSAJES["video_privado"])

    def test_mensaje_propio(self):
        e = errors.ErrorMiauki("no_es_video")
        self.assertEqual(e.codigo, "no_es_video")

    def test_mensaje_personalizado_amable(self):
        e = errors.ErrorMiauki("requiere_sesion",
                               "El tweet es de una cuenta protegida.")
        self.assertEqual(e.codigo, "requiere_sesion")
        self.assertEqual(str(e), "El tweet es de una cuenta protegida.")

    def test_codigo_invalido_explosa(self):
        with self.assertRaises(KeyError):
            errors.ErrorMiauki("no_existe")


class SinQuery(unittest.TestCase):
    def test_quita_la_query_del_log(self):
        t = errors.sin_query("fallo con https://r4---sn.googlevideo.com/videoplayback?expire=99&itag=22")
        self.assertNotIn("expire", t)
        self.assertIn("googlevideo.com/videoplayback", t)

    def test_texto_sin_urls_queda_igual(self):
        self.assertEqual(errors.sin_query("Video unavailable"), "Video unavailable")


class PlaylistMix(unittest.TestCase):
    """Tanda 20/11/2026: los Mix automáticos de YouTube tienen mensaje propio."""

    def test_el_mensaje_real_cae_en_su_codigo(self):
        real = ("ERROR: [youtube:tab] RDW4Wi3qLANOM: YouTube said: This "
                "playlist type is unviewable.")
        self.assertEqual(errors.codigo_de(real), "playlist_mix_no_visible")

    def test_el_mensaje_es_claro_y_sin_jerga(self):
        texto = errors.MENSAJES["playlist_mix_no_visible"].lower()
        self.assertIn("mix", texto)
        self.assertIn("playlist", texto)
        self.assertNotIn("unviewable", texto)
        self.assertNotIn("error", texto)


class VerificacionBot(unittest.TestCase):
    """Tanda 20/11/2026, paso 5: el aviso anti-bot tiene su propio código."""

    def test_el_mensaje_real_de_youtube_cae_en_su_codigo(self):
        real = ("ERROR: [youtube] K-jgTQxJLMg: Sign in to confirm you're not "
                "a bot. This helps protect our community. Use --cookies-from-"
                "browser or --cookies for the authentication.")
        self.assertEqual(errors.codigo_de(real), "youtube_verificacion_bot")

    def test_no_se_confunde_con_iniciar_sesion(self):
        self.assertNotEqual(errors.codigo_de("Sign in to confirm you're not a bot"),
                            "requiere_sesion")

    def test_el_mensaje_es_propio_y_amable(self):
        texto = errors.MENSAJES["youtube_verificacion_bot"].lower()
        self.assertIn("robot", texto)
        self.assertIn("probá de nuevo", texto)
        self.assertNotIn("iniciar sesión", texto)


if __name__ == "__main__":
    unittest.main()

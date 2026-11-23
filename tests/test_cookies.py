# -*- coding: utf-8 -*-
"""Fase 9, B2/B2b: cookies por archivo Netscape y por navegador, sin filtrarlas.

Lo que se prueba:
- el archivo se valida con `http.cookiejar` (formato Netscape) y solo se guarda
  su ruta; el contenido no se copia a los ajustes ni al log;
- el archivo gana sobre el navegador, y las dos vías llegan a yt-dlp (análisis,
  descarga) y a las vías de imágenes de X;
- de X se leen SOLO las cookies de x.com/twitter.com, en memoria;
- un archivo que falta o está roto da un error amable, nunca una excepción.

Todos los archivos de este test son de mentira: valores inventados, sin sesión.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import apoyo  # noqa: E402,F401  (aísla la carpeta de datos)

from miauki import paths  # noqa: E402
from miauki.core import analyzer, cookies, downloader, settings  # noqa: E402
from miauki.core.errors import ErrorMiauki  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
HTML = (RAIZ / "miauki" / "ui" / "index.html").read_text(encoding="utf-8")
JS = (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")
STRINGS = (RAIZ / "miauki" / "ui" / "js" / "strings.es.js").read_text(encoding="utf-8")

NETSCAPE = (
    "# Netscape HTTP Cookie File\n"
    "# archivo de prueba: valores inventados, ninguna sesión real\n"
    ".x.com\tTRUE\t/\tTRUE\t0\tauth_token\tvalor-secreto-auth\n"
    ".x.com\tTRUE\t/\tTRUE\t0\tct0\tvalor-secreto-ct0\n"
    ".twitter.com\tTRUE\t/\tTRUE\t0\tkdt\tvalor-secreto-kdt\n"
    ".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tno-es-de-x\n"
)


def escribir(directorio: str, contenido: str = NETSCAPE, nombre: str = "cookies.txt") -> Path:
    ruta = Path(directorio) / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


class ArchivoDeCookies(unittest.TestCase):
    def test_un_netscape_normal_sirve(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d)
            self.assertEqual(str(ruta), cookies.archivo_valido(str(ruta)))

    def test_sin_la_cabecera_no_sirve(self):
        """yt-dlp exige la cabecera Netscape; el validador usa el mismo criterio."""
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d, NETSCAPE.split("\n", 2)[2])
            with self.assertRaises(ErrorMiauki) as ctx:
                cookies.archivo_valido(str(ruta))
        self.assertEqual("cookies_archivo_invalido", ctx.exception.codigo)

    def test_un_archivo_que_no_existe(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ErrorMiauki) as ctx:
                cookies.archivo_valido(str(Path(d) / "no-esta.txt"))
        self.assertEqual("cookies_archivo_faltante", ctx.exception.codigo)

    def test_un_netscape_con_extension_cookies_sirve(self):
        """La extensión ya no es un requisito: el contenido manda."""
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d, NETSCAPE, "cookies.cookies")
            self.assertEqual(str(ruta), cookies.archivo_valido(str(ruta)))

    def test_un_contenido_que_no_es_cookies_no_sirve(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d, "esto no es nada\n" * 3, "cookies.dat")
            with self.assertRaises(ErrorMiauki) as ctx:
                cookies.archivo_valido(str(ruta))
        self.assertEqual("cookies_archivo_invalido", ctx.exception.codigo)

    def test_un_json_valido_sirve(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "cookies.json"
            ruta.write_text(json.dumps([
                {"name": "auth_token", "value": "valor-secreto-auth",
                 "domain": ".x.com", "path": "/"},
                {"name": "ct0", "value": "valor-secreto-ct0",
                 "domain": ".x.com", "path": "/"},
            ]), encoding="utf-8")
            self.assertEqual(str(ruta), cookies.archivo_valido(str(ruta)))

    def test_un_json_invalido_no_sirve(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "cookies.json"
            ruta.write_text('["hola"]', encoding="utf-8")
            with self.assertRaises(ErrorMiauki) as ctx:
                cookies.archivo_valido(str(ruta))
        self.assertEqual("cookies_archivo_invalido", ctx.exception.codigo)

    def test_basura_no_es_un_archivo_de_cookies(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d, "esto es una receta de milanesas\n" * 3)
            with self.assertRaises(ErrorMiauki) as ctx:
                cookies.archivo_valido(str(ruta))
        self.assertEqual("cookies_archivo_invalido", ctx.exception.codigo)

    def test_un_archivo_vacio_o_enorme_no_sirve(self):
        with tempfile.TemporaryDirectory() as d:
            vacio = escribir(d, "# Netscape HTTP Cookie File\n", "vacio.txt")
            with self.assertRaises(ErrorMiauki):
                cookies.archivo_valido(str(vacio))
            enorme = Path(d) / "enorme.txt"
            enorme.write_bytes(b"x" * (cookies.ARCHIVO_MAX + 1))
            with self.assertRaises(ErrorMiauki) as ctx:
                cookies.archivo_valido(str(enorme))
        self.assertEqual("cookies_archivo_invalido", ctx.exception.codigo)

    def test_una_ruta_que_no_es_texto(self):
        for basura in (None, 42, "", "   "):
            with self.assertRaises(ErrorMiauki):
                cookies.archivo_valido(basura)


class OpcionesParaYtdlp(unittest.TestCase):
    def test_el_archivo_gana_sobre_el_navegador(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d)
            op = cookies.opciones({"archivo_cookies": str(ruta),
                                   "navegador_cookies": "chrome"})
        self.assertEqual({"cookiefile": str(ruta)}, op)

    def test_un_json_se_convierte_a_netscape_temporal(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "cookies.json"
            ruta.write_text(json.dumps([
                {"name": "auth_token", "value": "v", "domain": ".x.com"},
            ]), encoding="utf-8")
            op = cookies.opciones({"archivo_cookies": str(ruta)})
        self.assertIn("cookiefile", op)
        self.assertTrue(Path(op["cookiefile"]).is_file())
        self.assertEqual("v", cookies._leer_jarra(op["cookiefile"]).__iter__().__next__().value)

    def test_un_archivo_borrado_avisa_en_las_opciones(self):
        """Una ruta vieja no debe terminar en un "pide iniciar sesión" a secas."""
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ErrorMiauki) as ctx:
                cookies.opciones({"archivo_cookies": str(Path(d) / "nada.txt")})
        self.assertEqual("cookies_archivo_faltante", ctx.exception.codigo)

    def test_sin_archivo_manda_el_navegador(self):
        op = cookies.opciones({"archivo_cookies": "", "navegador_cookies": "firefox"})
        self.assertEqual({"cookiesfrombrowser": ("firefox",)}, op)

    def test_brave_y_otros_chromium_son_navegadores_validos(self):
        for navegador in ("brave", "chromium", "opera", "vivaldi"):
            op = cookies.opciones({"archivo_cookies": "",
                                   "navegador_cookies": navegador})
            self.assertEqual({"cookiesfrombrowser": (navegador,)}, op)

    def test_sin_nada_no_hay_opciones(self):
        self.assertEqual({}, cookies.opciones({}))
        self.assertEqual({}, cookies.opciones({"navegador_cookies": "ninguno"}))

    def test_las_opciones_llegan_al_analisis_y_a_la_descarga(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d)
            ajustes = {"archivo_cookies": str(ruta), "navegador_cookies": "ninguno"}
            self.assertEqual(str(ruta), analyzer._opciones_ajustes(ajustes)["cookiefile"])
            solicitud = {"url_canonica": "https://www.youtube.com/watch?v=abc12345678",
                         "contenedor": "mp4", "extension": "mp4", "tipo": "video"}
            op = downloader.construir_opciones(solicitud, ajustes, d)
            self.assertEqual(str(ruta), op["cookiefile"])
            self.assertNotIn("cookiesfrombrowser", op)


class CookiesDeX(unittest.TestCase):
    def test_solo_se_leen_las_de_x_y_twitter(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d)
            cookie, csrf, error = cookies.para_x({"archivo_cookies": str(ruta),
                                                  "navegador_cookies": "ninguno"})
        self.assertIsNone(error)
        self.assertEqual("valor-secreto-ct0", csrf)
        self.assertIn("auth_token=valor-secreto-auth", cookie)
        self.assertIn("kdt=valor-secreto-kdt", cookie)
        self.assertNotIn("no-es-de-x", cookie)

    def test_sin_cookies_no_hay_error(self):
        self.assertEqual((None, None, None), cookies.para_x({"navegador_cookies": "ninguno"}))

    def test_para_x_funciona_con_un_json(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "cookies.json"
            ruta.write_text(json.dumps([
                {"name": "auth_token", "value": "valor-secreto-auth",
                 "domain": ".x.com"},
                {"name": "ct0", "value": "valor-secreto-ct0",
                 "domain": ".twitter.com"},
                {"name": "SID", "value": "no-es-de-x",
                 "domain": ".youtube.com"},
            ]), encoding="utf-8")
            cookie, csrf, error = cookies.para_x(
                {"archivo_cookies": str(ruta),
                 "navegador_cookies": "ninguno"})
        self.assertIsNone(error)
        self.assertEqual("valor-secreto-ct0", csrf)
        self.assertIn("auth_token=valor-secreto-auth", cookie)
        self.assertNotIn("no-es-de-x", cookie)

    def test_un_dominio_que_solo_termina_en_x_com_no_va(self):
        """`notx.com` termina en "x.com" pero no es de X: no se manda a X."""
        contenido = NETSCAPE + ".notx.com\tTRUE\t/\tTRUE\t0\trobada\tno-va\n"
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d, contenido)
            cookie, _csrf, error = cookies.para_x({"archivo_cookies": str(ruta),
                                                   "navegador_cookies": "ninguno"})
        self.assertIsNone(error)
        self.assertNotIn("no-va", cookie)
        self.assertIn("auth_token=valor-secreto-auth", cookie)

    def test_un_archivo_roto_da_un_error_amable(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d, "no soy un cookies.txt\n" * 3)
            cookie, csrf, error = cookies.para_x({"archivo_cookies": str(ruta),
                                                  "navegador_cookies": "ninguno"})
        self.assertIsNone(cookie)
        self.assertTrue(error)
        self.assertIn("Netscape", error)

    def test_si_el_navegador_no_se_puede_leer_sugiere_el_archivo(self):
        """Edge/Chrome con DPAPI: el aviso tiene que ofrecer la salida."""
        from unittest import mock

        with mock.patch("miauki.core.motor.ytdlp", side_effect=RuntimeError("DPAPI")):
            cookie, csrf, error = cookies.para_x({"navegador_cookies": "edge"})
        self.assertIsNone(cookie)
        self.assertIsNone(csrf)
        self.assertIn("Edge", error)
        self.assertIn("Firefox", error)
        self.assertIn("archivo de cookies", error)

    def test_un_archivo_borrado_despues_da_un_error_amable(self):
        with tempfile.TemporaryDirectory() as d:
            cookie, csrf, error = cookies.para_x(
                {"archivo_cookies": str(Path(d) / "nada.txt")})
        self.assertIsNone(cookie)
        self.assertIn("ya no está", error)


class NadaDeCookiesEnAjustesNiLog(unittest.TestCase):
    def test_los_ajustes_guardan_la_ruta_y_no_el_contenido(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d)
            archivo = Path(d) / "ajustes.json"
            settings.cambiar("archivo_cookies", str(ruta), ruta=archivo)
            guardado = json.loads(archivo.read_text(encoding="utf-8"))
        self.assertEqual(str(ruta), guardado["archivo_cookies"])
        for secreto in ("valor-secreto-auth", "valor-secreto-ct0", "valor-secreto-kdt"):
            self.assertNotIn(secreto, json.dumps(guardado))

    def test_las_cookies_no_aparecen_en_el_log(self):
        from miauki.core.logger import obtener_logger

        with tempfile.TemporaryDirectory() as d:
            ruta = escribir(d)
            obtener_logger().info("marcador de prueba de cookies")   # deja el log vivo
            cookies.para_x({"archivo_cookies": str(ruta), "navegador_cookies": "ninguno"})
            # Y la vía de error, que sí escribe en el log.
            cookies.para_x({"archivo_cookies": str(Path(d) / "borrado.txt")})
            logs = paths.dir_logs()
            texto = ""
            if logs.is_dir():
                for log in logs.glob("miauki.log*"):
                    texto += log.read_text(encoding="utf-8", errors="replace")
        # Si el log no se pudo leer, el test de abajo pasaría de casualidad.
        self.assertIn("marcador de prueba de cookies", texto)
        for secreto in ("valor-secreto-auth", "valor-secreto-ct0", "valor-secreto-kdt"):
            self.assertNotIn(secreto, texto)


class InterfazDelArchivoDeCookies(unittest.TestCase):
    def test_hay_boton_para_elegir_y_para_quitar(self):
        self.assertIn("data-cookies-elegir", HTML)
        self.assertIn("data-cookies-quitar", HTML)
        self.assertRegex(HTML, r'data-cookies-quitar[^>]*hidden')

    def test_los_textos_existen_y_avisan_de_la_privacidad(self):
        for clave in ("ajustes.cookiesElegir", "ajustes.cookiesQuitar",
                      "ajustes.cookiesSinArchivo", "ajustes.cookiesConArchivo",
                      "ajustes.cookiesPrivacidad"):
            self.assertIn('"%s":' % clave, STRINGS)
        self.assertIn("no lo compartas", STRINGS)

    def test_los_botones_llaman_al_puente(self):
        self.assertIn("pywebview.api.elegir_archivo_cookies()", JS)
        self.assertIn("pywebview.api.quitar_archivo_cookies()", JS)
        self.assertIn('data-cookies-archivo', JS)

    def test_el_error_de_cookies_lleva_a_ajustes(self):
        self.assertIn('"cookies_archivo_invalido"', JS)
        self.assertIn('"cookies_archivo_faltante"', JS)


if __name__ == "__main__":
    unittest.main()

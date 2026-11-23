# -*- coding: utf-8 -*-
"""Tests del puente api.py: siempre {ok, data|error}, sin excepciones a la UI.

Contrato de error (§7): {"ok": false, "error": {"codigo", "mensaje"}}.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki import app_info  # noqa: E402
from miauki.api import Api  # noqa: E402
from miauki.core.errors import ErrorMiauki, MENSAJES  # noqa: E402


class Puente(unittest.TestCase):
    def test_ping_devuelve_ok_y_pong(self):
        r = Api().ping()
        self.assertEqual(r, {"ok": True, "data": "pong"})

    def test_info_devuelve_nombre_y_version(self):
        r = Api().info()
        self.assertTrue(r["ok"])
        self.assertIn("Miauki YT", r["data"]["nombre"])
        self.assertEqual(r["data"]["version"], "1.0.0")

    def test_info_trae_licencia_y_donacion(self):
        datos = Api().info()["data"]
        self.assertIn("GPL", datos["licencia"])
        self.assertTrue(datos["enlaces"]["paypal"].startswith("https://"))
        self.assertTrue(datos["donacion"]["alias"])
        self.assertIn("incentivo", datos["donacion"]["texto"])

    def test_info_en_ingles_devuelve_los_textos_en_ingles(self):
        datos = Api().info("en")["data"]
        self.assertTrue(datos["descripcion"].startswith("Video and audio"))
        self.assertIn("or later", datos["licencia"])
        self.assertIn("tip", datos["donacion"]["texto"])

    def test_copiar_usdt_copia_la_direccion_de_app_info(self):
        copiadas = []

        def falso_copiar(texto):
            copiadas.append(texto)
            return True

        r = Api(copia=falso_copiar).copiar_usdt()
        self.assertTrue(r["data"]["copiado"])
        self.assertEqual(copiadas, [app_info.USDT_DONACION])
        self.assertEqual(r["data"]["direccion"], app_info.USDT_DONACION)

    def test_copiar_alias_usa_el_texto_de_app_info(self):
        copiado = []

        def falso_copiar(texto):
            copiado.append(texto)
            return True

        r = Api(copia=falso_copiar).copiar_alias()
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["alias"], copiado[0])
        self.assertTrue(r["data"]["copiado"])

    def test_error_interno_no_escapa(self):
        from miauki.api import seguro

        class Rota(Api):
            @seguro
            def explota(self):
                raise RuntimeError("boom")

        r = Rota().explota()
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "error_desconocido")
        self.assertNotIn("boom", r["error"]["mensaje"])

    def test_error_de_analisis_con_codigo_y_mensaje_amable(self):
        with mock.patch("miauki.core.analyzer.analizar",
                        side_effect=ErrorMiauki("video_privado")):
            r = Api().analizar("https://www.youtube.com/watch?v=x")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "video_privado")
        self.assertEqual(r["error"]["mensaje"], MENSAJES["video_privado"])
        self.assertNotIn("private", r["error"]["mensaje"].lower())

    def test_analizar_ok_devuelve_data(self):
        esperado = {"id_solicitud": "abc", "tipo": "video",
                    "titulo": "Video de prueba"}
        with mock.patch("miauki.core.analyzer.analizar",
                        return_value=dict(esperado)):
            r = Api().analizar("https://www.youtube.com/watch?v=x")
        self.assertEqual(r, {"ok": True, "data": esperado})

    def test_analizar_sin_string_es_link_invalido(self):
        for malo in (None, 42, "   ", ["https://x.com"]):
            r = Api().analizar(malo)
            self.assertFalse(r["ok"], repr(malo))
            self.assertEqual(r["error"]["codigo"], "link_invalido")


SNAPSHOT = {
    "url_canonica": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "tipo": "video",
    "selector": "137+140",
    "contenedor": "mp4",
    "titulo": "Me at the zoo",
    "miniatura": "data:image/png;base64,AAA",
    "con_subs": True,
}


class _ColaFalsa:
    def __init__(self, falla=None):
        self.agregados = []
        self.playlists = []
        self.acciones = []
        self.lista = []
        self.falla = falla

    def agregar(self, snapshot):
        if self.falla:
            raise self.falla
        self.agregados.append(dict(snapshot))
        return "abc123"

    def agregar_playlist(self, snapshot):
        if self.falla:
            raise self.falla
        # Igual que la Cola real: sin entradas es error amable, no crash.
        if not isinstance(snapshot.get("entradas"), list) \
                or not snapshot["entradas"]:
            raise ErrorMiauki("playlist_sin_entradas")
        self.playlists.append(dict(snapshot))
        return ["id1", "id2"]

    def pausar(self, ident):
        self.acciones.append(("pausar", ident))
        return True

    def reanudar(self, ident):
        self.acciones.append(("reanudar", ident))
        return True

    def cancelar(self, ident):
        self.acciones.append(("cancelar", ident))
        return True

    def borrar(self, ident):
        self.acciones.append(("borrar", ident))
        return True

    def reintentar(self, ident):
        self.acciones.append(("reintentar", ident))
        return True

    def pausar_todo(self):
        self.acciones.append(("pausar_todo", None))
        return 2

    def reanudar_todo(self):
        self.acciones.append(("reanudar_todo", None))
        return 3

    def cancelar_todo(self):
        self.acciones.append(("cancelar_todo", None))
        return 1

    def limpiar_historial(self):
        self.acciones.append(("limpiar_historial", None))
        return 4

    def items(self):
        return list(self.lista)


class PuenteCola(unittest.TestCase):
    def _api(self, cola=None):
        return Api(cola=cola or _ColaFalsa())

    def test_agregar_descarga_devuelve_id_y_valida_el_snapshot(self):
        cola = _ColaFalsa()
        r = self._api(cola).agregar_descarga(dict(SNAPSHOT))
        self.assertEqual(r, {"ok": True, "data": {"id": "abc123"}})
        # El snapshot se normaliza: se agregan kbps, resolucion, sitio
        # (el sitio sale del link, no de lo que mande la interfaz) y
        # url_directa (Paso 3, opción "Original"; None si no aplica).
        self.assertEqual(cola.agregados,
                         [dict(SNAPSHOT, kbps=None, resolucion=None,
                               sitio="youtube", url_directa=None)])

    def test_snapshot_invalido_da_entrada_invalida(self):
        cola = _ColaFalsa()
        api = self._api(cola)
        for malo in (None, "url", 42, {}, {"url_canonica": "https://x"},
                     {"tipo": "video"}, {"url_canonica": "https://x",
                                         "tipo": "baile"}):
            r = api.agregar_descarga(malo)
            self.assertFalse(r["ok"], repr(malo))
        self.assertEqual(cola.agregados, [])

    def test_url_vacia_en_el_snapshot_da_link_invalido(self):
        r = self._api().agregar_descarga(dict(SNAPSHOT, url_canonica="  "))
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "link_invalido")

    # ---------- playlists (plan de playlists, Pasos 5-7) ----------

    def test_agregar_playlist_valida_y_encola_cada_entrada(self):
        cola = _ColaFalsa()
        snapshot = dict(SNAPSHOT, titulo="Lista",
                        entradas=[dict(SNAPSHOT, titulo="v1"),
                                  dict(SNAPSHOT, titulo="v2")])
        r = self._api(cola).agregar_playlist(snapshot)
        self.assertEqual(r, {"ok": True, "data": {"ids": ["id1", "id2"],
                                                  "cantidad": 2,
                                                  "bloques": 1}})
        self.assertEqual(len(cola.playlists), 1)
        # Cada entrada sale normalizada (sitio por link, kbps/resolucion).
        limpias = cola.playlists[0]["entradas"]
        self.assertEqual([e["titulo"] for e in limpias], ["v1", "v2"])
        for e in limpias:
            self.assertEqual(e["sitio"], "youtube")

    def test_agregar_playlist_con_entrada_invalida_da_entrada_invalida(self):
        snapshot = dict(SNAPSHOT, entradas=[dict(SNAPSHOT, tipo="baile")])
        r = self._api().agregar_playlist(snapshot)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "entrada_invalida")

    def test_agregar_playlist_muy_larga_da_playlist_muy_larga(self):
        snapshot = dict(SNAPSHOT, entradas=[
            dict(SNAPSHOT, titulo=f"v{i}") for i in range(601)])
        r = self._api().agregar_playlist(snapshot)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "playlist_muy_larga")
        self.assertEqual(r["error"]["mensaje"], MENSAJES["playlist_muy_larga"])

    def test_agregar_playlist_vacia_da_error_amable(self):
        # El borde rechaza entradas=[] (lista imposible); sin la clave
        # entradas, la Cola real da playlist_sin_entradas.
        r = self._api().agregar_playlist(dict(SNAPSHOT, entradas=[]))
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "entrada_invalida")

    def test_agregar_playlist_que_no_es_playlist_da_error_amable(self):
        r = self._api().agregar_playlist(dict(SNAPSHOT))
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "playlist_sin_entradas")

    def test_cola_llena_sigue_siendo_error_amable(self):
        cola = _ColaFalsa(falla=ErrorMiauki("cola_llena"))
        r = self._api(cola).agregar_descarga(dict(SNAPSHOT))
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "cola_llena")
        self.assertIn("10", r["error"]["mensaje"])

    def test_las_acciones_pasan_el_id_a_la_cola(self):
        cola = _ColaFalsa()
        api = self._api(cola)
        self.assertEqual(api.pausar_descarga("abc"),
                         {"ok": True, "data": True})
        self.assertEqual(api.reanudar_descarga("abc")["data"], True)
        self.assertEqual(api.cancelar_descarga("abc")["data"], True)
        self.assertEqual(api.reintentar_descarga("abc")["data"], True)
        self.assertEqual(api.borrar_descarga("abc")["data"], True)
        self.assertEqual(cola.acciones, [
            ("pausar", "abc"), ("reanudar", "abc"), ("cancelar", "abc"),
            ("reintentar", "abc"), ("borrar", "abc")])

    def test_globales_de_cola_llaman_al_backend(self):
        # Plan archivos y cola, paso 2: los botones globales pasan por el
        # puente y devuelven la cantidad que tocó la Cola.
        cola = _ColaFalsa()
        api = self._api(cola)
        self.assertEqual(api.pausar_todo(), {"ok": True, "data": 2})
        self.assertEqual(api.reanudar_todo(), {"ok": True, "data": 3})
        self.assertEqual(api.cancelar_todo(), {"ok": True, "data": 1})
        self.assertEqual(api.limpiar_historial_cola(), {"ok": True, "data": 4})
        self.assertEqual(cola.acciones, [
            ("pausar_todo", None), ("reanudar_todo", None),
            ("cancelar_todo", None), ("limpiar_historial", None)])

    def test_id_que_no_es_texto_devuelve_false_sin_llamar(self):
        cola = _ColaFalsa()
        api = self._api(cola)
        for malo in (None, 42, ["abc"], {}):
            r = api.pausar_descarga(malo)
            self.assertEqual(r, {"ok": True, "data": False}, repr(malo))
        self.assertEqual(cola.acciones, [])

    def test_cola_actual_devuelve_la_lista(self):
        cola = _ColaFalsa()
        cola.lista = [{"id": "x", "estado": "terminada"}]
        r = self._api(cola).cola_actual()
        self.assertEqual(r["data"], cola.lista)


class Carpetas(unittest.TestCase):
    """B5: abrir carpeta y cambiar carpeta (puente mínimo, sin vista aún)."""

    def setUp(self):
        import json as _json
        import tempfile
        from pathlib import Path
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.carpeta = Path(self._tmp.name) / "descargas"
        self.carpeta.mkdir()
        self.ruta_ajustes = Path(self._tmp.name) / "ajustes.json"
        self.ruta_ajustes.write_text(_json.dumps(
            {"carpeta_descargas": str(self.carpeta)}), encoding="utf-8")
        self.abiertas = []

    def _api(self, dialogo=None):
        return Api(abre=self.abiertas.append, dialogo_carpeta=dialogo,
                   ruta_ajustes=self.ruta_ajustes)

    def test_abrir_carpeta_abre_la_ruta_dada(self):
        r = self._api().abrir_carpeta(str(self.carpeta))
        self.assertEqual(r, {"ok": True, "data": True})
        self.assertEqual(self.abiertas, [str(self.carpeta)])

    def test_abrir_carpeta_sin_ruta_usa_los_ajustes(self):
        r = self._api().abrir_carpeta()
        self.assertEqual(r["data"], True)
        self.assertEqual(self.abiertas, [str(self.carpeta)])

    def test_abrir_carpeta_inexistente_da_false(self):
        r = self._api().abrir_carpeta(str(self.carpeta / "no-existe"))
        self.assertEqual(r, {"ok": True, "data": False})
        self.assertEqual(self.abiertas, [])

    def test_abrir_carpeta_id_raro_da_link_invalido(self):
        r = self._api().abrir_carpeta(42)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "link_invalido")

    def test_cambiar_carpeta_guarda_el_ajuste(self):
        nueva = Path(self._tmp.name) / "otra"
        nueva.mkdir()
        r = self._api(dialogo=lambda: (str(nueva),)).cambiar_carpeta()
        self.assertEqual(r, {"ok": True, "data": str(nueva)})
        ajustes = json.loads(self.ruta_ajustes.read_text(encoding="utf-8"))
        self.assertEqual(ajustes["carpeta_descargas"], str(nueva))

    def test_cambiar_carpeta_cancelada_da_none(self):
        r = self._api(dialogo=lambda: ()).cambiar_carpeta()
        self.assertEqual(r, {"ok": True, "data": None})
        ajustes = json.loads(self.ruta_ajustes.read_text(encoding="utf-8"))
        self.assertEqual(ajustes["carpeta_descargas"], str(self.carpeta))

    def test_abrir_carpeta_ajena_da_false_sin_abrir(self):
        # P0.7: solo la carpeta de ajustes (o de un ítem de la cola).
        ajena = Path(self._tmp.name).parent  # fuera de la carpeta de ajustes
        r = self._api().abrir_carpeta(str(ajena))
        self.assertEqual(r, {"ok": True, "data": False})
        self.assertEqual(self.abiertas, [])

    def test_abrir_carpeta_con_escape_da_false(self):
        r = self._api().abrir_carpeta(
            str(self.carpeta / ".." / "afuera"))
        self.assertEqual(r, {"ok": True, "data": False})
        self.assertEqual(self.abiertas, [])

    def test_cambiar_carpeta_peligrosa_se_rechaza(self):
        api = self._api(dialogo=lambda: ("C:\\Windows",))
        r = api.cambiar_carpeta()
        self.assertEqual(r, {"ok": True, "data": None})
        ajustes = json.loads(self.ruta_ajustes.read_text(encoding="utf-8"))
        self.assertEqual(ajustes["carpeta_descargas"], str(self.carpeta))

    def test_mostrar_archivo_de_la_cola_lo_revela(self):
        archivo = self.carpeta / "video.mp4"
        archivo.write_bytes(b"x")

        class ColaConItem:
            def items(self):
                return [{"id": "x", "ruta": str(archivo)}]

        revelados = []
        api = Api(cola=ColaConItem(), ruta_ajustes=self.ruta_ajustes,
                  abre_archivo=revelados.append, abre=self.abiertas.append)
        self.assertEqual(api.mostrar_archivo(str(archivo)),
                         {"ok": True, "data": True})
        self.assertEqual(revelados, [str(archivo)])

    def test_mostrar_archivo_ajeno_da_false(self):
        ajeno = Path(self._tmp.name) / "ajeno.mp4"
        ajeno.write_bytes(b"x")
        r = self._api().mostrar_archivo(str(ajeno))
        self.assertEqual(r, {"ok": True, "data": False})

    # ---------- archivo de cookies (Fase 9, B2b) ----------

    def _cookies_falsas(self, contenido=None):
        ruta = Path(self._tmp.name) / "cookies.txt"
        ruta.write_text(contenido or (
            "# Netscape HTTP Cookie File\n"
            ".x.com\tTRUE\t/\tTRUE\t0\tauth_token\tinventado\n"), encoding="utf-8")
        return ruta

    def test_elegir_archivo_cookies_guarda_solo_la_ruta(self):
        ruta = self._cookies_falsas()
        api = Api(dialogo_archivo=lambda: (str(ruta),), ruta_ajustes=self.ruta_ajustes)
        r = api.elegir_archivo_cookies()
        self.assertEqual(r, {"ok": True, "data": {"archivo": str(ruta)}})
        ajustes = json.loads(self.ruta_ajustes.read_text(encoding="utf-8"))
        self.assertEqual(ajustes["archivo_cookies"], str(ruta))
        self.assertNotIn("inventado", json.dumps(ajustes))

    def test_elegir_archivo_cancelado_no_cambia_nada(self):
        api = Api(dialogo_archivo=lambda: (), ruta_ajustes=self.ruta_ajustes)
        r = api.elegir_archivo_cookies()
        self.assertEqual(r, {"ok": True, "data": {"archivo": ""}})

    def test_un_archivo_invalido_da_error_amable(self):
        ruta = self._cookies_falsas("no soy un archivo de cookies\n")
        api = Api(dialogo_archivo=lambda: (str(ruta),), ruta_ajustes=self.ruta_ajustes)
        r = api.elegir_archivo_cookies()
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "cookies_archivo_invalido")
        self.assertIn("Netscape", r["error"]["mensaje"])
        self.assertNotIn("archivo_cookies", self.ruta_ajustes.read_text(encoding="utf-8"))

    def test_un_archivo_borrado_da_error_amable(self):
        api = Api(dialogo_archivo=lambda: (str(Path(self._tmp.name) / "no.txt"),),
                  ruta_ajustes=self.ruta_ajustes)
        r = api.elegir_archivo_cookies()
        self.assertEqual(r["error"]["codigo"], "cookies_archivo_faltante")

    def test_quitar_el_archivo_lo_deja_vacio(self):
        ruta = self._cookies_falsas()
        api = Api(dialogo_archivo=lambda: (str(ruta),), ruta_ajustes=self.ruta_ajustes)
        api.elegir_archivo_cookies()
        r = api.quitar_archivo_cookies()
        self.assertEqual(r, {"ok": True, "data": {"archivo": ""}})
        ajustes = json.loads(self.ruta_ajustes.read_text(encoding="utf-8"))
        self.assertEqual(ajustes["archivo_cookies"], "")


class HistorialPuente(unittest.TestCase):
    """F6 B1: todo por ID, la ruta la pone el historial (nunca la interfaz)."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.archivo = self.dir / "video.mp4"
        self.archivo.write_bytes(b"x")
        self.entrada = {
            "id": "a" * 32, "titulo": "Video", "sitio": "youtube",
            "tipo": "video", "calidad": "1080p", "contenedor": "mp4",
            "ruta": str(self.archivo), "peso": 1,
            "url_canonica": "https://www.youtube.com/watch?v=x",
            "miniatura": "", "selector": "137+140", "resolucion": 1080,
            "kbps": None, "con_subs": False,
        }
        self.acciones = []

    def _historial(self, entradas=None):
        entrada = self.entrada

        class Falso:
            def listar(yo):
                return [dict(entrada)]

            def obtener(yo, ident):
                return dict(entrada) if ident == entrada["id"] else None

            def quitar(yo, ident):
                self.acciones.append(("quitar", ident))
                return ident == entrada["id"]

            def borrar(yo):
                self.acciones.append(("borrar",))
                return 1

        return Falso()

    def _api(self, cola=None, historial=None):
        return Api(cola=cola or _ColaFalsa(), historial=historial or self._historial(),
                   abre=self.acciones.append, abre_archivo=self.acciones.append)

    def test_listar_marca_si_el_archivo_existe(self):
        r = self._api().listar_historial()
        self.assertTrue(r["data"][0]["existe"])
        self.archivo.unlink()
        self.assertFalse(self._api().listar_historial()["data"][0]["existe"])

    def test_volver_a_bajar_arma_el_snapshot_desde_el_historial(self):
        cola = _ColaFalsa()
        r = self._api(cola).volver_a_bajar("a" * 32)
        self.assertEqual(r, {"ok": True, "data": {"id": "abc123"}})
        self.assertEqual(cola.agregados[0]["selector"], "137+140")
        self.assertEqual(cola.agregados[0]["resolucion"], 1080)

    def test_id_desconocido_da_error_amable(self):
        r = self._api().volver_a_bajar("b" * 32)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["codigo"], "historial_no_encontrado")

    def test_abrir_carpeta_y_mostrar_archivo_por_id(self):
        api = self._api()
        self.assertTrue(api.abrir_carpeta_historial("a" * 32)["data"])
        self.assertTrue(api.mostrar_archivo_historial("a" * 32)["data"])
        self.assertEqual(self.acciones, [str(self.dir), str(self.archivo)])

    def test_archivo_inexistente_no_abre_nada(self):
        self.archivo.unlink()
        api = self._api()
        r = api.mostrar_archivo_historial("a" * 32)
        self.assertEqual(r["error"]["codigo"], "archivo_no_encontrado")
        self.assertEqual(self.acciones, [])

    def test_quitar_y_borrar_pasan_por_el_historial(self):
        api = self._api()
        self.assertTrue(api.quitar_del_historial("a" * 32)["data"])
        self.assertEqual(api.borrar_historial()["data"], 1)
        self.assertEqual(self.acciones, [("quitar", "a" * 32), ("borrar",)])

    def test_ruta_del_historial_no_se_puede_inyectar(self):
        # El puente no recibe rutas: solo IDs. Un ID que parece ruta no abre nada.
        r = self._api().abrir_carpeta_historial("C:\\Windows")
        self.assertEqual(r["error"]["codigo"], "historial_no_encontrado")


class AcercaPuente(unittest.TestCase):
    """A4: enlaces por lista blanca, diagnóstico sin datos personales."""

    def test_comprobar_actualizacion_app_sin_fuente_configurada(self):
        """Plan 19/11: el botón de actualizaciones de la app está listo pero
        todavía no hay fuente (app_info.URL_ACTUALIZACIONES_APP vacía)."""
        from miauki import app_info
        self.assertEqual(app_info.URL_ACTUALIZACIONES_APP, "")
        r = Api().comprobar_actualizacion_app()
        self.assertEqual(r, {"ok": True, "data": {"configurado": False}})

    def test_abrir_enlace_instagram_abre_la_url_fija(self):
        abiertas = []
        api = Api(abre_url=abiertas.append)
        self.assertEqual(api.abrir_enlace("instagram"),
                         {"ok": True, "data": True})
        self.assertEqual(abiertas,
                         ["https://www.instagram.com/tusrecursosdigitaless/"])

    def test_abrir_enlace_paypal_abre_la_url_fija(self):
        abiertas = []
        api = Api(abre_url=abiertas.append)
        self.assertEqual(api.abrir_enlace("paypal"),
                         {"ok": True, "data": True})
        self.assertEqual(abiertas,
                         ["https://www.paypal.com/paypalme/ezequielgottwald"])

    def test_abrir_enlace_rechaza_urls_y_claves_desconocidas(self):
        abiertas = []
        api = Api(abre_url=abiertas.append)
        for malo in ("https://evil.example", "javascript:alert(1)", "otra",
                     None, 42):
            r = api.abrir_enlace(malo)
            self.assertFalse(r["ok"], repr(malo))
            self.assertEqual(r["error"]["codigo"], "link_invalido")
        self.assertEqual(abiertas, [])

    def test_abrir_registros_abre_solo_la_carpeta_de_logs(self):
        from miauki import paths
        abiertas = []
        Api(abre=abiertas.append).abrir_registros()
        self.assertEqual(abiertas, [str(paths.dir_logs())])

    def test_diagnostico_sin_rutas_links_ni_titulos(self):
        capturado = []

        def copiar(texto):
            capturado.append(texto)
            return True

        r = Api(copia=copiar).copiar_diagnostico()
        self.assertTrue(r["data"]["copiado"])
        texto = capturado[0]
        for prohibido in ("C:\\", "Users", "http", "watch?v", "cookie"):
            self.assertNotIn(prohibido, texto)
        self.assertIn("Miauki YT 1.0.0", texto)
        self.assertIn("WebView2", texto)

    def test_abrir_licencias_usa_el_archivo_junto_al_exe(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "LICENCIAS.txt"
            archivo.write_text("GPLv3", encoding="utf-8")
            abiertos = []
            with mock.patch("miauki.api.paths.dir_del_programa",
                            return_value=Path(tmp)), \
                    mock.patch("miauki.api.paths.recursos", return_value=Path(tmp)):
                r = Api(abre_archivo=abiertos.append).abrir_enlace("licencias")
            self.assertEqual(r, {"ok": True, "data": True})
            self.assertEqual(abiertos, [str(archivo)])

    def test_abrir_licencias_sin_archivo_da_error_amable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("miauki.api.paths.dir_del_programa",
                            return_value=Path(tmp)), \
                    mock.patch("miauki.api.paths.recursos", return_value=Path(tmp)):
                r = Api().abrir_enlace("licencias")
        self.assertEqual(r["error"]["codigo"], "licencias_faltan")


class PegarYSoltar(unittest.TestCase):
    """Fase 7, B2: Ctrl+V y arrastrar validan el link en el borde."""

    def test_pegar_link_valido_lo_devuelve_canonico(self):
        with mock.patch("miauki.api.clipboard.texto_del_portapapeles",
                        return_value="mirá: https://youtu.be/jNQXAC9IVRw?si=x"):
            r = Api().pegar_link()
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["url"],
                         "https://www.youtube.com/watch?v=jNQXAC9IVRw")

    def test_pegar_texto_sin_link(self):
        with mock.patch("miauki.api.clipboard.texto_del_portapapeles",
                        return_value="hola, ¿cómo va?"):
            r = Api().pegar_link()
        self.assertTrue(r["ok"])
        self.assertIsNone(r["data"]["url"])
        self.assertEqual(r["data"]["motivo"], "no_link")

    def test_pegar_un_archivo_del_explorador_no_es_link(self):
        with mock.patch("miauki.api.clipboard.texto_del_portapapeles",
                        return_value="C:\\Users\\Maki\\video.mp4"):
            r = Api().pegar_link()
        self.assertTrue(r["ok"])
        self.assertIsNone(r["data"]["url"])
        self.assertEqual(r["data"]["motivo"], "no_link")

    def test_pegar_un_esquema_raro_no_es_link(self):
        for texto in ("javascript:alert(1)", "file:///C:/Windows/win.ini",
                      "ftp://ejemplo.com/video.mp4"):
            with mock.patch("miauki.api.clipboard.texto_del_portapapeles",
                            return_value=texto):
                r = Api().pegar_link()
            self.assertIsNone(r["data"]["url"], texto)

    def test_validar_texto_de_un_arrastre(self):
        r = Api().validar_texto("https://www.tiktok.com/@a/video/1")
        self.assertEqual(r["data"]["url"],
                         "https://www.tiktok.com/@a/video/1")

    def test_validar_texto_de_un_archivo_no_es_link(self):
        r = Api().validar_texto("C:\\Users\\Maki\\video.mp4")
        self.assertIsNone(r["data"]["url"])

    def test_validar_texto_de_tipo_raro_no_rompe(self):
        r = Api().validar_texto(None)
        self.assertTrue(r["ok"])
        self.assertIsNone(r["data"]["url"])


if __name__ == "__main__":
    unittest.main()

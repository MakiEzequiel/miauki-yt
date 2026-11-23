# -*- coding: utf-8 -*-
"""Descargador (Fase 4 B2): opciones, progreso monótono, errores y cancelación.

Todo corre sin red: `descargar` acepta un YoutubeDL falso (ydl_ctor) que
simula el progreso y devuelve la ruta final como haría yt-dlp.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import downloader  # noqa: E402
from miauki.core import errors  # noqa: E402
from miauki.core.errors import ErrorMiauki  # noqa: E402

VIDEO = {
    "url_canonica": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "tipo": "video",
    "selector": "137+140",
    "contenedor": "mp4",
    "titulo": "Me at the zoo",
}
MUSICA = {
    "url_canonica": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "tipo": "musica",
    "selector": "bestaudio",
    "contenedor": None,
    "kbps": 256,
    "titulo": "Me at the zoo",
}
IMAGEN = {
    "url_canonica": "https://pbs.twimg.com/media/abc.jpg",
    "tipo": "imagen",
    "selector": None,
    "contenedor": None,
    "titulo": "foto",
}
AJUSTES = {
    "carpeta_descargas": r"C:\dl",
    "idioma_subs": "es",
    "incluir_subs": True,
    "navegador_cookies": "chrome",
}


class _RelojFalso:
    def __init__(self):
        self.ahora = 100.0

    def __call__(self):
        self.ahora += 0.1
        return self.ahora


class _YdlFalso:
    """YoutubeDL falso: registra las opciones y simula el ciclo de descarga.

    `pasos` son los estados que pasa a los progress_hooks antes de volver:
    por defecto uno downloading al 50% y uno finished.
    """

    def __init__(self, opciones, info=None, error=None, pasos=None,
                 subs_error=None):
        self.opciones = opciones
        self._info = info
        self._error = error
        self._pasos = pasos if pasos is not None else [
            {"status": "downloading", "downloaded_bytes": 50,
             "total_bytes": 100, "speed": 1000.0, "eta": 1},
            {"status": "finished", "filename": r"C:\dl\Me at the zoo.mp4"},
        ]
        self._subs_error = subs_error
        self.llamadas = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        self.llamadas += 1
        if self._error is not None and self.llamadas == 1:
            raise self._error
        if self._subs_error is not None and self.llamadas > 1:
            raise self._subs_error
        if self.llamadas == 1:
            for paso in self._pasos:
                for hook in self.opciones.get("progress_hooks", []):
                    hook(dict(paso, filename=paso.get(
                        "filename") or r"C:\dl\Me at the zoo.mp4"))
        return self._info


def _ctor_que_registra(registro, **kwargs):
    def ctor(opciones):
        ydl = _YdlFalso(opciones, **kwargs)
        registro.append(ydl)
        return ydl
    return ctor


class ConstruirOpciones(unittest.TestCase):
    def test_video_usa_el_selector_y_el_contenedor_del_snapshot(self):
        op = downloader.construir_opciones(VIDEO, AJUSTES,
                                           AJUSTES["carpeta_descargas"])
        self.assertEqual(op["format"], "137+140")
        self.assertEqual(op["merge_output_format"], "mp4")
        self.assertTrue(op["noplaylist"])
        self.assertIn("%(title).100s.%(ext)s", op["outtmpl"])
        self.assertTrue(op["outtmpl"].startswith(AJUSTES["carpeta_descargas"]))

    def test_musica_es_bestaudio_con_mp3_en_el_kbps_elegido(self):
        op = downloader.construir_opciones(MUSICA, AJUSTES,
                                           AJUSTES["carpeta_descargas"])
        self.assertEqual(op["format"], "bestaudio")
        self.assertNotIn("merge_output_format", op)
        self.assertEqual(op["postprocessors"], [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "256",
        }])

    def test_imagen_baja_la_url_directa_sin_postproceso(self):
        op = downloader.construir_opciones(IMAGEN, AJUSTES,
                                           AJUSTES["carpeta_descargas"])
        self.assertEqual(op["format"], "best")
        self.assertNotIn("postprocessors", op)
        self.assertNotIn("merge_output_format", op)

    def test_las_cookies_del_navegador_llegan_a_ytdlp(self):
        op = downloader.construir_opciones(VIDEO, AJUSTES,
                                           AJUSTES["carpeta_descargas"])
        self.assertEqual(op["cookiesfrombrowser"], ("chrome",))

    def test_ffmpeg_local_como_ubicacion(self):
        op = downloader.construir_opciones(VIDEO, AJUSTES,
                                           AJUSTES["carpeta_descargas"])
        self.assertIn("ffmpeg_location", op)

    def test_los_hooks_entran_en_las_opciones(self):
        hook = lambda d: None
        op = downloader.construir_opciones(VIDEO, AJUSTES,
                                           AJUSTES["carpeta_descargas"],
                                           hook=hook, pp_hook=hook)
        self.assertEqual(op["progress_hooks"], [hook])
        self.assertEqual(op["postprocessor_hooks"], [hook])


class OpcionesSubs(unittest.TestCase):
    def test_segunda_pasada_solo_de_subs(self):
        op = downloader.opciones_subs(r"C:\dl", AJUSTES, "es")
        self.assertTrue(op["skip_download"])
        self.assertTrue(op["writesubtitles"])
        self.assertFalse(op["writeautomaticsub"])
        self.assertTrue(op["ignoreerrors"])
        self.assertEqual(op["subtitleslangs"], ["es"])   # un solo idioma

    def test_subtitulo_automatico_usa_writeautomaticsub(self):
        op = downloader.opciones_subs(r"C:\dl", AJUSTES, "en", automatico=True)
        self.assertFalse(op["writesubtitles"])
        self.assertTrue(op["writeautomaticsub"])
        self.assertEqual(op["subtitleslangs"], ["en"])

    def test_el_nombre_base_manda_en_el_outtmpl(self):
        op = downloader.opciones_subs(r"C:\dl", AJUSTES, "es", nombre="foto")
        self.assertIn(r"foto.%(ext)s", op["outtmpl"])


class ElegirSubs(unittest.TestCase):
    """Regla: preferir el idioma de los ajustes; si no está, el otro; si
    ninguno está, no bajar nada (ni fallar la descarga principal)."""

    def test_prefiere_el_idioma_de_los_ajustes(self):
        info = {"subtitles": {"es": [{}], "en": [{}]}}
        self.assertEqual(downloader._elegir_subs(info, "es"), ("es", False))

    def test_cae_al_otro_idioma_si_el_preferido_no_esta(self):
        info = {"subtitles": {"en": [{}]}}
        self.assertEqual(downloader._elegir_subs(info, "es"), ("en", False))

    def test_manual_tiene_prioridad_sobre_automatico(self):
        info = {"subtitles": {"en": [{}]},
                "automatic_captions": {"es": [{}]}}
        self.assertEqual(downloader._elegir_subs(info, "es"), ("en", False))

    def test_solo_automatico_del_otro_idioma(self):
        info = {"automatic_captions": {"en": [{}]}}
        self.assertEqual(downloader._elegir_subs(info, "es"), ("en", True))

    def test_sin_subs_no_baja_nada(self):
        info = {"subtitles": {"de": [{}]}}
        self.assertEqual(downloader._elegir_subs(info, "es"), (None, False))
        self.assertEqual(downloader._elegir_subs({}, "es"), (None, False))


class Tope(unittest.TestCase):
    """Decisión 3d.5: progreso monótono, máximo ~4 eventos por segundo."""

    def test_no_emite_mas_de_cuatro_por_segundo(self):
        reloj = _RelojFalso()
        emitidos = []
        tope = downloader._Tope(emitidos.append, reloj=reloj, espera=0.25)
        for pct in (10, 20, 30, 40, 50, 60):
            tope.avisar({"porcentaje": pct})
        # ventana de 0.25 s con llamadas cada 0.1 s: emite la 1ª y la 4ª
        self.assertEqual(len(emitidos), 2)

    def test_el_porcentaje_nunca_baja(self):
        reloj = _RelojFalso()
        emitidos = []
        tope = downloader._Tope(emitidos.append, reloj=reloj, espera=0.25)
        tope.avisar({"porcentaje": 80})
        reloj.ahora += 1
        tope.avisar({"porcentaje": 30})   # yt-dlp puede volver atrás
        reloj.ahora += 1
        tope.avisar({"porcentaje": 90})
        # el 30 nunca se emite: sale clamped al 80 ya visto
        self.assertEqual([e["porcentaje"] for e in emitidos], [80, 80, 90])

    def test_el_ultimo_aviso_fuerza_siempre(self):
        reloj = _RelojFalso()
        emitidos = []
        tope = downloader._Tope(emitidos.append, reloj=reloj, espera=0.25)
        tope.avisar({"porcentaje": 5})
        tope.avisar({"porcentaje": 100}, forzar=True)
        self.assertEqual([e["porcentaje"] for e in emitidos], [5, 100])


class Descargar(unittest.TestCase):
    def test_devuelve_la_ruta_que_indico_ytdlp(self):
        registro = []
        info = {"requested_downloads": [
            {"filepath": r"C:\dl\Me at the zoo.mp4"}],
            "subtitles": {"es": [{}]}}
        resultado = downloader.descargar(
            VIDEO, AJUSTES, ydl_ctor=_ctor_que_registra(registro, info=info))
        self.assertEqual(resultado["ruta"], r"C:\dl\Me at the zoo.mp4")
        self.assertEqual(len(registro), 2)  # descarga + 2ª pasada de subs

    def test_archivo_fuera_de_la_carpeta_se_rechaza(self):
        # P0.7: el archivo final nunca sale de la carpeta elegida.
        registro = []
        info = {"requested_downloads": [{"filepath": r"C:\otro\evil.mp4"}]}
        with self.assertRaises(ErrorMiauki) as ctx:
            downloader.descargar(
                VIDEO, AJUSTES, ydl_ctor=_ctor_que_registra(registro, info=info))
        self.assertEqual(ctx.exception.codigo, "entrada_invalida")

    def test_el_error_de_ytdlp_se_vuelve_error_amable(self):
        registro = []
        ctor = _ctor_que_registra(
            registro, error=Exception("ERROR: Video unavailable"))
        with self.assertRaises(ErrorMiauki) as ctx:
            downloader.descargar(VIDEO, AJUSTES, ydl_ctor=ctor)
        self.assertEqual(ctx.exception.codigo, "video_eliminado")

    def test_recibe_el_progreso_del_fake(self):
        registro = []
        info = {"requested_downloads": [
            {"filepath": r"C:\dl\Me at the zoo.mp4"}]}
        avises = []
        downloader.descargar(
            VIDEO, AJUSTES,             progreso=avises.append,
            ydl_ctor=_ctor_que_registra(registro, info=info))
        # llamadas dentro de <0.25 s: solo la primera y la final (forzada)
        self.assertGreaterEqual(len(avises), 1)
        self.assertEqual(avises[0]["fase"], "descarga")
        self.assertEqual(avises[0]["porcentaje"], 50.0)
        self.assertEqual(avises[-1]["porcentaje"], 100.0)

    def test_si_fallan_los_subs_la_descarga_no_se_rompe(self):
        registro = []
        info = {"requested_downloads": [
            {"filepath": r"C:\dl\Me at the zoo.mp4"}],
            "subtitles": {"es": [{}]}}
        ctor = _ctor_que_registra(registro, info=info,
                                  subs_error=Exception("no subs"))
        resultado = downloader.descargar(
            VIDEO, AJUSTES, ydl_ctor=ctor)
        self.assertEqual(resultado["ruta"], r"C:\dl\Me at the zoo.mp4")
        self.assertEqual(len(registro), 2)  # 2ª pasada de subtítulos

    def test_sin_subs_activos_no_hay_segunda_pasada(self):
        registro = []
        info = {"requested_downloads": [
            {"filepath": r"C:\dl\Me at the zoo.mp4"}],
            "subtitles": {"es": [{}]}}
        ajustes = dict(AJUSTES, incluir_subs=False)
        downloader.descargar(VIDEO, ajustes,
                             ydl_ctor=_ctor_que_registra(registro, info=info))
        self.assertEqual(len(registro), 1)

    def test_video_sin_subtitulos_no_hace_segunda_pasada(self):
        # incluir_subs activo, pero el video no tiene es ni en: no baja nada
        # y la descarga principal no se toca.
        registro = []
        info = {"requested_downloads": [
            {"filepath": r"C:\dl\Me at the zoo.mp4"}],
            "subtitles": {"de": [{}]}}
        downloader.descargar(VIDEO, AJUSTES,
                             ydl_ctor=_ctor_que_registra(registro, info=info))
        self.assertEqual(len(registro), 1)

    def test_original_con_url_directa_baja_sin_ytdlp(self):
        # Paso 3: Snapchat (opción "Original") baja la URL directa directo,
        # sin yt-dlp (su filtro rechaza la extensión rara).
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ajustes = dict(AJUSTES, carpeta_descargas=tmp.name)
        solicitud = dict(VIDEO, url_directa="data:video/mp4;base64,AAAA",
                         selector="best", resolucion=None)
        # La URL data: no es http(s): debe rechazarse como link inválido.
        with self.assertRaises(ErrorMiauki) as ctx:
            downloader.descargar(solicitud, ajustes)
        self.assertEqual(ctx.exception.codigo, "link_invalido")

    def test_cancelar_limpia_parciales_y_cancela(self):
        with tempfile.TemporaryDirectory() as carpeta:
            parcials = Path(carpeta) / "Me at the zoo.mp4.part"
            parcials.write_bytes(b"x" * 10)
            cancelar = threading.Event()
            cancelar.set()

            def ctor(opciones):
                nombre = str(Path(carpeta) / "Me at the zoo.mp4")
                ydl = _YdlFalso(opciones, info={}, pasos=[
                    {"status": "downloading", "downloaded_bytes": 1,
                     "total_bytes": 10, "filename": nombre}])
                return ydl

            with self.assertRaises(downloader.Cancelada):
                downloader.descargar(VIDEO, AJUSTES, cancelar=cancelar,
                                     ydl_ctor=ctor)
            self.assertFalse(parcials.exists())

    def test_cancelar_durante_postproceso_borra_el_archivo_final(self):
        """La cancelación que llega durante el ffmpeg (procesando) se
        respeta: el archivo final se borra y la descarga queda cancelada.
        El mock no corre hooks (simula que el postproceso ya terminó), así
        que el único punto que ve la señal es el chequeo posterior."""
        with tempfile.TemporaryDirectory() as carpeta:
            final = Path(carpeta) / "Me at the zoo.mp4"
            final.write_bytes(b"x" * 10)
            cancelar = threading.Event()
            cancelar.set()   # llegó durante el postproceso (ffmpeg)
            info = {"requested_downloads": [{"filepath": str(final)}]}

            def ctor(opciones):
                return _YdlFalso(opciones, info=info, pasos=[])

            ajustes = dict(AJUSTES, carpeta_descargas=carpeta)
            with self.assertRaises(downloader.Cancelada):
                downloader.descargar(VIDEO, ajustes, cancelar=cancelar,
                                     ydl_ctor=ctor)
            self.assertFalse(final.exists())


class _YdlQueFalla:
    def __init__(self, mensaje):
        self._mensaje = mensaje

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        raise Exception(self._mensaje)


class ReintentoFormato(unittest.TestCase):
    """P0.5: si la calidad pedida ya no existe, reanaliza y reintenta 1 vez."""

    def _ctor(self):
        estado = {"llamadas": 0, "formatos": []}

        def ctor(opciones):
            estado["llamadas"] += 1
            estado["formatos"].append(opciones.get("format"))
            if estado["llamadas"] == 1:
                return _YdlQueFalla(
                    "ERROR: Requested format is not available")
            return _YdlFalso(opciones, info={"requested_downloads": [
                {"filepath": r"C:\dl\Me at the zoo.mp4"}]})

        return ctor, estado

    def test_reanaliza_en_silencio_y_reintenta_una_vez(self):
        ctor, estado = self._ctor()
        nuevo = "bestvideo[height<=1080]+bestaudio/best"
        with mock.patch("miauki.core.downloader.analyzer.analizar",
                        return_value={"calidades": [
                            {"resolucion": 1080, "selector": nuevo}]}):
            r = downloader.descargar(dict(VIDEO, resolucion=1080), AJUSTES,
                                     ydl_ctor=ctor)
        self.assertEqual(estado["llamadas"], 2)
        self.assertEqual(estado["formatos"], ["137+140", nuevo])
        self.assertEqual(Path(r["ruta"]).name, "Me at the zoo.mp4")

    def test_si_el_reanalisis_no_da_selector_queda_el_error(self):
        ctor, estado = self._ctor()
        with mock.patch("miauki.core.downloader.analyzer.analizar",
                        side_effect=Exception("sin red")):
            with self.assertRaises(ErrorMiauki) as ctx:
                downloader.descargar(dict(VIDEO, resolucion=1080), AJUSTES,
                                     ydl_ctor=ctor)
        self.assertEqual(ctx.exception.codigo, "calidad_no_disponible")
        self.assertEqual(estado["llamadas"], 1)


class ReintentoVerificacionBot(unittest.TestCase):
    """Tanda 20/11/2026, paso 5: el aviso anti-bot se reintenta 2 veces."""

    def _ctor(self):
        estado = {"llamadas": 0}

        def ctor(opciones):
            estado["llamadas"] += 1
            if estado["llamadas"] < 3:
                return _YdlQueFalla(
                    "ERROR: [youtube] abc: Sign in to confirm you're not a bot")
            return _YdlFalso(opciones, info={"requested_downloads": [
                {"filepath": r"C:\dl\Me at the zoo.mp4"}]})

        return ctor, estado

    def test_reintenta_dos_veces_y_descarga(self):
        ctor, estado = self._ctor()
        with mock.patch.object(errors, "ESPERA_BOT", 0):
            r = downloader.descargar(dict(VIDEO), AJUSTES, ydl_ctor=ctor)
        self.assertEqual(estado["llamadas"], 3)
        self.assertEqual(Path(r["ruta"]).name, "Me at the zoo.mp4")

    def test_si_sigue_el_aviso_informa_el_codigo_nuevo(self):
        def ctor(opciones):
            return _YdlQueFalla("Sign in to confirm you're not a bot")

        with mock.patch.object(errors, "ESPERA_BOT", 0), \
                mock.patch.object(errors, "ESPERAS_PACIENTES", (0, 0, 0)):
            with self.assertRaises(ErrorMiauki) as ctx:
                downloader.descargar(dict(VIDEO), AJUSTES, ydl_ctor=ctor)
        self.assertEqual(ctx.exception.codigo, "youtube_verificacion_bot")

    def test_espera_paciente_antes_de_rendirse(self):
        """Paso 3: 2 reintentos cortos + 3 esperas crecientes."""
        estado = {"llamadas": 0}

        def ctor(opciones):
            estado["llamadas"] += 1
            return _YdlQueFalla("Sign in to confirm you're not a bot")

        esperas = []
        with mock.patch.object(errors, "ESPERA_BOT", 0), \
                mock.patch.object(errors, "ESPERAS_PACIENTES", (5.0, 10.0, 20.0)), \
                mock.patch.object(downloader.time, "sleep", side_effect=esperas.append):
            with self.assertRaises(ErrorMiauki):
                downloader.descargar(dict(VIDEO), AJUSTES, ydl_ctor=ctor)
        self.assertEqual(estado["llamadas"], 6)
        self.assertEqual(esperas, [0, 0, 5.0, 10.0, 20.0])

    def test_rota_el_cliente_de_youtube(self):
        """Paso 2: cada reintento anti-bot imita otra app de YouTube."""
        vistos = []

        def ctor(opciones):
            cliente = (opciones.get("extractor_args") or {}).get("youtube", {})
            vistos.append(cliente.get("player_client"))
            if len(vistos) == 1:
                return _YdlQueFalla("Sign in to confirm you're not a bot")
            return _YdlFalso(opciones, info={"requested_downloads": [
                {"filepath": r"C:\dl\Me at the zoo.mp4"}]})

        with mock.patch.object(errors, "ESPERA_BOT", 0):
            downloader.descargar(dict(VIDEO), AJUSTES, ydl_ctor=ctor)
        self.assertEqual(vistos, [None, ["android"]])


class _YdlQueCrea:
    """YoutubeDL falso que crea el archivo real en la ruta del outtmpl."""

    def __init__(self, opciones, ext="mp4"):
        self.opciones = opciones
        self.ext = ext

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        if self.opciones.get("skip_download"):
            return {"subtitles": {}}          # 2ª pasada de subtítulos
        ruta = self.opciones["outtmpl"].replace("%(ext)s", self.ext)
        Path(ruta).write_bytes(b"contenido")
        return {"requested_downloads": [{"filepath": ruta}]}


class NoSobrescribir(unittest.TestCase):
    """P0.6a: dos descargas del mismo video no se pisan (nombre " (2)")."""

    def _correr(self, carpeta, ext="mp4"):
        ajustes = dict(AJUSTES, carpeta_descargas=carpeta, incluir_subs=False)
        return downloader.descargar(
            VIDEO, ajustes, ydl_ctor=lambda op: _YdlQueCrea(op, ext))

    def test_segunda_descarga_va_a_nombre_2(self):
        with tempfile.TemporaryDirectory() as carpeta:
            r1 = self._correr(carpeta)
            r2 = self._correr(carpeta)
            self.assertEqual(Path(r1["ruta"]).name, "Me at the zoo.mp4")
            self.assertEqual(Path(r2["ruta"]).name, "Me at the zoo (2).mp4")
            self.assertTrue(Path(r1["ruta"]).exists())
            self.assertTrue(Path(r2["ruta"]).exists())

    def test_tercera_va_a_nombre_3(self):
        with tempfile.TemporaryDirectory() as carpeta:
            self._correr(carpeta)
            self._correr(carpeta)
            r3 = self._correr(carpeta)
            self.assertEqual(Path(r3["ruta"]).name, "Me at the zoo (3).mp4")

    def test_otra_extension_misma_base_tambien_cuenta(self):
        # si ya existe "Me at the zoo.mp3", el video usa "Me at the zoo (2)"
        with tempfile.TemporaryDirectory() as carpeta:
            (Path(carpeta) / "Me at the zoo.mp3").write_bytes(b"x")
            (Path(carpeta) / "Me at the zoo.es.srt").write_bytes(b"x")
            r = self._correr(carpeta)
            self.assertEqual(Path(r["ruta"]).name, "Me at the zoo (2).mp4")


class LimpiaRestos(unittest.TestCase):
    """ajustes 21/11: al completar, no quedan parciales del mismo nombre."""

    def test_descarga_ok_limpia_parciales_del_mismo_nombre(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ajustes = dict(AJUSTES, carpeta_descargas=carpeta, incluir_subs=False)
            (Path(carpeta) / "Me at the zoo.mp4.part").write_bytes(b"x")
            (Path(carpeta) / "Me at the zoo.f137.mp4").write_bytes(b"x")
            r = downloader.descargar(VIDEO, ajustes,
                                     ydl_ctor=lambda op: _YdlQueCrea(op))
            self.assertEqual(Path(r["ruta"]).name, "Me at the zoo.mp4")
            self.assertFalse(
                (Path(carpeta) / "Me at the zoo.mp4.part").exists())
            self.assertFalse(
                (Path(carpeta) / "Me at the zoo.f137.mp4").exists())
            self.assertTrue(Path(r["ruta"]).exists())


class TituloRealDePlaylist(unittest.TestCase):
    """Plan archivos y cola, paso 1: el archivo se guarda con el título real,
    sin el prefijo [Bloque X/Y] que solo se ve en la fila de la Cola."""

    def test_el_archivo_usa_titulo_real(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ajustes = dict(AJUSTES, carpeta_descargas=carpeta, incluir_subs=False)
            pedido = dict(VIDEO, titulo="[Bloque 1/1] [1/2] Me at the zoo",
                          _titulo_real="Me at the zoo")
            r = downloader.descargar(pedido, ajustes,
                                     ydl_ctor=lambda op: _YdlQueCrea(op))
            self.assertEqual(Path(r["ruta"]).name, "Me at the zoo.mp4")


class Pausar(unittest.TestCase):
    def test_pausa_conserva_parciales_y_entrega_los_vistos(self):
        # Decisión 3d.8: la pausa corta el hilo PERO conserva .part (resumen)
        with tempfile.TemporaryDirectory() as carpeta:
            nombre = str(Path(carpeta) / "Me at the zoo.mp4")
            parcial = Path(nombre + ".part")
            parcial.write_bytes(b"x" * 10)
            pausar = threading.Event()
            pausar.set()

            def ctor(opciones):
                return _YdlFalso(opciones, info={}, pasos=[
                    {"status": "downloading", "downloaded_bytes": 1,
                     "total_bytes": 10, "filename": nombre}])

            with self.assertRaises(downloader.Pausada) as ctx:
                downloader.descargar(VIDEO, AJUSTES, pausar=pausar,
                                     ydl_ctor=ctor)
            self.assertTrue(parcial.exists())  # .part queda para resumir
            self.assertIn(nombre, ctx.exception.vistos)
            # la cola puede limpiar más tarde (borrar/cancelar desde pausa)
            downloader.limpiar(ctx.exception.vistos)
            self.assertFalse(parcial.exists())

    def test_cancelar_tiene_prioridad_sobre_pausa(self):
        cancelar = threading.Event()
        pausar = threading.Event()
        cancelar.set()
        pausar.set()

        def ctor(opciones):
            return _YdlFalso(opciones, info={}, pasos=[
                {"status": "downloading", "downloaded_bytes": 1,
                 "total_bytes": 10, "filename": r"C:\dl\x.mp4"}])

        with self.assertRaises(downloader.Cancelada):
            downloader.descargar(VIDEO, AJUSTES, cancelar=cancelar,
                                 pausar=pausar, ydl_ctor=ctor)


class _YdlConParteAbierta:
    """YoutubeDL que deja el .part ABIERTO mientras corre (dest_stream)."""

    def __init__(self, opciones, nombre):
        self.opciones = opciones
        self._nombre = nombre
        self._abierto = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        self._abierto = open(self._nombre + ".part", "wb")
        self._abierto.write(b"x")
        for hook in self.opciones.get("progress_hooks", []):
            hook({"status": "downloading", "downloaded_bytes": 1,
                  "total_bytes": 10, "filename": self._nombre})
        self._abierto.close()
        return {}


class ArchivosBloqueados(unittest.TestCase):
    """Windows: si yt-dlp deja el .part abierto, borrar/renombrar falla
    (WinError 32). El stream debe cerrarse cuando corta cancelar o pausar.
    """

    def _ctor_con_parte_abierta(self, nombre):
        return lambda opciones: _YdlConParteAbierta(opciones, nombre)

    def test_tras_cancelar_el_parte_no_queda_bloqueado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            nombre = str(Path(carpeta) / "video")
            cancelar = threading.Event()
            cancelar.set()
            ctor = self._ctor_con_parte_abierta(nombre)
            with self.assertRaises(downloader.Cancelada):
                downloader.descargar(VIDEO, AJUSTES, cancelar=cancelar,
                                     ydl_ctor=ctor)
            # Al cancelar se limpian los temporales: o el .part ya no está,
            # o si sigue (limpiar no llegó a borrarlo) hay que poder borrarlo.
            parte = Path(nombre + ".part")
            if parte.exists():
                parte.unlink()                   # fallaría si sigue abierto

    def test_tras_pausar_el_parte_no_queda_bloqueado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            nombre = str(Path(carpeta) / "video")
            pausar = threading.Event()
            pausar.set()
            ctor = self._ctor_con_parte_abierta(nombre)
            with self.assertRaises(downloader.Pausada):
                downloader.descargar(VIDEO, AJUSTES, pausar=pausar,
                                     ydl_ctor=ctor)
            parte = Path(nombre + ".part")
            self.assertTrue(parte.exists())     # pausa conserva el .part
            parte.unlink()                      # pero sin handle abierto


class EliminadoPasajero(unittest.TestCase):
    """Ajustes 21/11: un "eliminado" pasajero en YouTube se reintenta una vez."""

    def test_eliminado_pasajero_se_reintenta_y_termina_bien(self):
        estado = {"llamadas": 0}

        def ctor(opciones):
            estado["llamadas"] += 1
            if estado["llamadas"] == 1:
                return _YdlQueFalla(
                    "ERROR: Video unavailable. This video has been removed by "
                    "the uploader")
            return _YdlFalso(opciones, info={"requested_downloads": [
                {"filepath": r"C:\dl\Me at the zoo.mp4"}]})

        r = downloader.descargar(VIDEO, AJUSTES, ydl_ctor=ctor)
        self.assertGreaterEqual(estado["llamadas"], 2)
        self.assertEqual(Path(r["ruta"]).name, "Me at the zoo.mp4")

    def test_eliminado_real_falla_despues_de_un_reintento(self):
        def ctor(opciones):
            return _YdlQueFalla(
                "ERROR: Video unavailable. This video has been removed by the "
                "uploader")

        with self.assertRaises(ErrorMiauki) as ctx:
            downloader.descargar(VIDEO, AJUSTES, ydl_ctor=ctor)
        self.assertEqual(ctx.exception.codigo, "video_eliminado")

    def test_no_se_reintenta_eliminado_en_otros_sitios(self):
        registro = []
        otro = dict(VIDEO, url_canonica="https://vimeo.com/123")
        ctor = _ctor_que_registra(
            registro,
            error=RuntimeError("ERROR: Video unavailable"),
            info={"requested_downloads": [
                {"filepath": r"C:\dl\Me at the zoo.mp4"}]})
        with self.assertRaises(ErrorMiauki) as ctx:
            downloader.descargar(otro, AJUSTES, ydl_ctor=ctor)
        self.assertEqual(ctx.exception.codigo, "video_eliminado")
        self.assertEqual(len(registro), 1)   # sin reintento


if __name__ == "__main__":
    unittest.main()

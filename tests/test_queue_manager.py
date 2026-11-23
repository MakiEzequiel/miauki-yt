# -*- coding: utf-8 -*-
"""Cola de descargas (Fase 4 B3): máquina de estados del spec §4.

Sin red y sin descargador real: `Cola(bajar=falso, emitir=registrador)`.
Los hilos se esperan con eventos y `_esperar` (polls con tope), no con
sleeps sueltos.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from miauki.core import downloader, history, queue_manager  # noqa: E402
from miauki.core.errors import ErrorMiauki  # noqa: E402

SNAPSHOT = {
    "url_canonica": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "tipo": "video",
    "selector": "137+140",
    "contenedor": "mp4",
    "titulo": "Me at the zoo",
    "miniatura": "data:image/png;base64,AAA",
}


def _esperar(cond, seg=3.0):
    limite = time.time() + seg
    while time.time() < limite:
        if cond():
            return True
        time.sleep(0.01)
    return False


class _Registrador:
    def __init__(self):
        self.eventos = []

    def __call__(self, evento, datos=None):
        self.eventos.append((evento, datos))

    def ultimos(self, evento):
        return [d for e, d in self.eventos if e == evento]

    def ultimo(self, evento):
        lista = self.ultimos(evento)
        return lista[-1] if lista else None


class _BajadorFalso:
    """descargar() falso: `comportamiento(solicitud, progreso, cancelar,
    pausar)` decide qué hace; por defecto avanza al 50% y termina."""

    def __init__(self, comportamiento=None):
        self.llamadas = []
        self.concorrencia_max = 0
        self._activos = 0
        self._comportamiento = comportamiento

    def __call__(self, solicitud, ajustes, progreso=None, cancelar=None,
                 pausar=None):
        self.llamadas.append(dict(solicitud))
        self._activos += 1
        self.concorrencia_max = max(self.concorrencia_max, self._activos)
        try:
            if self._comportamiento:
                return self._comportamiento(solicitud, progreso, cancelar,
                                            pausar)
            if progreso:
                progreso({"fase": "descarga", "porcentaje": 50.0,
                          "descargado": 50, "total": 100,
                          "velocidad": None, "restante": None})
            # Ventana breve escuchando señales: estabiliza los tests de
            # pausa/cancelación (antes, un bajar instantáneo ganaba la
            # carrera y la señal llegaba tarde).
            fin = time.time() + 0.15
            while time.time() < fin:
                if cancelar is not None and cancelar.is_set():
                    raise downloader.Cancelada()
                if pausar is not None and pausar.is_set():
                    raise downloader.Pausada([r"C:\dl\x.mp4.part"])
                time.sleep(0.005)
            return {"ruta": r"C:\dl\Me at the zoo.mp4"}
        finally:
            self._activos -= 1


def _nueva_cola(comportamiento=None, ajustes=None, analizar=None):
    bajador = _BajadorFalso(comportamiento)
    registrador = _Registrador()
    # analizar por defecto es un stub vacío: el refresco de reintentar no debe
    # salir a la red en los tests.
    cola = queue_manager.Cola(
        bajar=bajador, emitir=registrador,
        ajustes=ajustes or {"carpeta_descargas": "C:\\dl"},
        ruta_cola=Path(tempfile.mkdtemp(prefix="miauki_cola_")) / "cola.json",
        analizar=analizar if analizar is not None else (lambda url, **kw: {}))
    return cola, bajador, registrador


def _bloqueante(evento):
    """Comportamiento: espera a que se suelte `evento`; respeta señales."""
    def _hacer(solicitud, progreso, cancelar, pausar):
        while not evento.wait(0.01):
            if cancelar is not None and cancelar.is_set():
                raise downloader.Cancelada()
            if pausar is not None and pausar.is_set():
                raise downloader.Pausada([r"C:\dl\x.mp4.part"])
        return {"ruta": r"C:\dl\Me at the zoo.mp4"}
    return _hacer


class FlujoBasico(unittest.TestCase):
    def test_agregar_descarga_termina_y_emite_eventos(self):
        cola, bajador, reg = _nueva_cola()
        ident = cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "terminada"))
        item = cola.items()[0]
        self.assertEqual(item["ruta"], r"C:\dl\Me at the zoo.mp4")
        self.assertEqual(item["titulo"], "Me at the zoo")
        estados = [i["estado"] for lista in reg.ultimos("cola")
                   for i in lista]
        self.assertIn("descargando", estados)
        self.assertIn("terminada", estados)
        progreso = reg.ultimo("progreso")
        self.assertEqual(progreso["id"], ident)
        self.assertEqual(progreso["porcentaje"], 50.0)

    def test_eventos_cola_no_muestran_lo_interno(self):
        cola, _, reg = _nueva_cola()
        cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()))
        for lista in reg.ultimos("cola"):
            for item in lista:
                self.assertFalse([c for c in item if c.startswith("_")])


class Playlist(unittest.TestCase):
    """Paso 4 del plan de playlists: encolar la lista completa."""

    def _playlist(self, n):
        entradas = [dict(SNAPSHOT, titulo=f"Video {i}") for i in range(1, n + 1)]
        return dict(SNAPSHOT, titulo="Lista", entradas=entradas)

    def test_playlist_de_5_encola_5_con_prefijo(self):
        cola, bajador, _ = _nueva_cola()
        ids = cola.agregar_playlist(self._playlist(5))
        self.assertEqual(len(ids), 5)
        self.assertTrue(_esperar(lambda: len(bajador.llamadas) == 5))
        titulos = [i["titulo"] for i in cola.items()]
        self.assertEqual(titulos, [f"[Bloque 1/1] [{i}/5] Video {i}"
                                   for i in range(1, 6)])
        # MAX_ACTIVAS: el trabajador único nunca baja 2 a la vez.
        self.assertLessEqual(bajador.concorrencia_max, 1)

    def test_titulo_real_para_archivo_e_historial(self):
        # Plan archivos y cola, paso 1: el ítem guarda el título real para el
        # archivo y el historial; el prefijo [Bloque X/Y] queda solo en la Cola.
        cola, _, _ = _nueva_cola()
        cola.agregar_playlist(self._playlist(2))
        internos = cola._items
        self.assertEqual(internos[0]["_titulo_real"], "Video 1")
        self.assertTrue(internos[0]["titulo"].startswith("[Bloque 1/1] [1/2]"))

    def test_playlist_450_en_3_bloques(self):
        cola, _, _ = _nueva_cola()
        ids = cola.agregar_playlist(self._playlist(450))
        self.assertEqual(len(ids), 450)
        items = cola.items()
        self.assertEqual(items[0]["titulo"], "[Bloque 1/3] [1/450] Video 1")
        self.assertEqual(items[199]["titulo"], "[Bloque 1/3] [200/450] Video 200")
        self.assertEqual(items[200]["titulo"], "[Bloque 2/3] [201/450] Video 201")
        self.assertEqual(items[399]["titulo"], "[Bloque 2/3] [400/450] Video 400")
        self.assertEqual(items[400]["titulo"], "[Bloque 3/3] [401/450] Video 401")
        self.assertEqual(items[-1]["titulo"], "[Bloque 3/3] [450/450] Video 450")
        self.assertEqual(items[0]["bloque"], "1/3")
        self.assertEqual(items[-1]["bloque"], "3/3")

    def test_playlist_600_en_3_bloques(self):
        cola, _, _ = _nueva_cola()
        ids = cola.agregar_playlist(self._playlist(600))
        self.assertEqual(len(ids), 600)
        items = cola.items()
        self.assertEqual(items[0]["bloque"], "1/3")
        self.assertEqual(items[400]["bloque"], "3/3")
        self.assertEqual(items[-1]["bloque"], "3/3")
        self.assertEqual(items[-1]["titulo"], "[Bloque 3/3] [600/600] Video 600")

    def test_pausar_todo_y_reanudar_todo(self):
        # Plan archivos y cola, paso 2: pausa congela la descarga en curso y
        # la espera; reanudar las devuelve a la cola de espera.
        libre = threading.Event()
        cola, _, _ = _nueva_cola(_bloqueante(libre))
        ids = cola.agregar_playlist(self._playlist(3))
        self.assertTrue(_esperar(lambda: any(
            i["estado"] == "descargando" for i in cola.items())))
        self.assertEqual(cola.pausar_todo(), 3)
        self.assertTrue(_esperar(lambda: all(
            i["estado"] == "pausa" for i in cola.items())))
        self.assertEqual(cola.reanudar_todo(), 3)
        self.assertTrue(_esperar(lambda: not any(
            i["estado"] == "pausa" for i in cola.items())))
        # Los ítems siguen en la lista y son los mismos.
        self.assertEqual([i["id"] for i in cola.items()], ids)
        libre.set()   # libera la descarga para que el hilo cierre limpio

    def test_pausar_todo_solo_cuenta_lo_que_pausa(self):
        cola, _, _ = _nueva_cola()
        self.assertEqual(cola.pausar_todo(), 0)     # cola vacía
        ids = cola.agregar_playlist(self._playlist(2))
        cola.pausar_todo()
        self.assertEqual(cola.pausar_todo(), 0)     # ya están pausadas

    def test_limpiar_historial_borra_todo_lo_terminado(self):
        # Tacho (paso 2): quita terminadas, canceladas, error e interrumpidas;
        # los archivos en disco no se tocan (solo se sacan filas).
        cola, _, _ = _nueva_cola()
        cola.agregar_playlist(self._playlist(3))
        self.assertTrue(_esperar(lambda: all(
            i["estado"] == "terminada" for i in cola.items())))
        self.assertEqual(cola.limpiar_historial(), 3)
        self.assertEqual(cola.items(), [])
        # Sin activas se puede repetir y no rompe.
        self.assertEqual(cola.limpiar_historial(), 0)

    def test_limpiar_historial_deja_lo_activo(self):
        cola, _, _ = _nueva_cola()
        ids = cola.agregar_playlist(self._playlist(2))
        cola.pausar_todo()
        self.assertEqual(cola.limpiar_historial(), 0)   # pausa no es borrable
        self.assertEqual([i["id"] for i in cola.items()], ids)

    def test_descarga_suelta_no_lleva_bloque(self):
        cola, _, _ = _nueva_cola()
        cola.agregar(dict(SNAPSHOT))
        self.assertNotIn("bloque", cola.items()[0])

    def test_playlist_de_10_encola_10(self):
        cola, _, _ = _nueva_cola()
        ids = cola.agregar_playlist(self._playlist(10))
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(cola.items()), 10)
        self.assertTrue(_esperar(lambda: all(
            i["estado"] == "terminada" for i in cola.items())))

    def test_playlist_de_10_no_pisa_el_tope_de_espera(self):
        # La playlist NO compite con MAX_ESPERA (10): los 10 entran de una.
        cola, _, _ = _nueva_cola()
        ids = cola.agregar_playlist(self._playlist(10))
        self.assertEqual(len(ids), 10)

    def test_playlist_vacia_da_error(self):
        cola, _, _ = _nueva_cola()
        with self.assertRaises(ErrorMiauki) as ctx:
            cola.agregar_playlist(dict(SNAPSHOT, entradas=[]))
        self.assertEqual(ctx.exception.codigo, "playlist_sin_entradas")

    def test_playlist_muy_larga_da_error(self):
        cola, _, _ = _nueva_cola()
        with self.assertRaises(ErrorMiauki) as ctx:
            cola.agregar_playlist(self._playlist(601))
        self.assertEqual(ctx.exception.codigo, "playlist_muy_larga")

    def test_playlist_sin_entradas_da_error(self):
        cola, _, _ = _nueva_cola()
        with self.assertRaises(ErrorMiauki):
            cola.agregar_playlist(dict(SNAPSHOT))


class Activos(unittest.TestCase):
    def test_activos_cuenta_solo_lo_que_sigue_en_curso(self):
        liberar = threading.Event()
        cola, _, _ = _nueva_cola(comportamiento=_bloqueante(liberar))
        cola.agregar(dict(SNAPSHOT))                # 1 descargando
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "descargando"))
        cola.agregar(dict(SNAPSHOT, titulo="2"))    # 1 en espera
        self.assertEqual(cola.activos(), 2)
        cola.agregar(dict(SNAPSHOT, titulo="3"))
        self.assertEqual(cola.activos(), 3)
        liberar.set()
        self.assertTrue(_esperar(lambda: cola.activos() == 0))


class TopeDeCola(unittest.TestCase):
    def test_cola_llena_da_error_amable(self):
        liberar = threading.Event()
        cola, _, _ = _nueva_cola(comportamiento=_bloqueante(liberar))
        cola.agregar(dict(SNAPSHOT))          # 1 activa
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "descargando"))
        for i in range(10):                    # 10 en espera
            cola.agregar(dict(SNAPSHOT, titulo="t%d" % i))
        with self.assertRaises(ErrorMiauki) as ctx:
            cola.agregar(dict(SNAPSHOT))
        self.assertEqual(ctx.exception.codigo, "cola_llena")
        self.assertIn("10", ctx.exception.mensaje)
        liberar.set()


class UnActiva(unittest.TestCase):
    def test_una_sola_descarga_activa_a_la_vez(self):
        cola, bajador, _ = _nueva_cola()
        for _ in range(3):
            cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: len(bajador.llamadas) == 3
                                 and all(i["estado"] == "terminada"
                                         for i in cola.items())))
        self.assertEqual(bajador.concorrencia_max, 1)


class Cancelar(unittest.TestCase):
    def test_cancelar_en_espera_no_llama_al_descargador(self):
        liberar = threading.Event()
        cola, bajador, _ = _nueva_cola(comportamiento=_bloqueante(liberar))
        cola.agregar(dict(SNAPSHOT))                  # se queda descargando
        segundo = cola.agregar(dict(SNAPSHOT, titulo="2"))
        self.assertTrue(_esperar(lambda: len(bajador.llamadas) == 1))
        self.assertTrue(cola.cancelar(segundo))
        self.assertEqual(cola.items()[1]["estado"], "cancelada")
        liberar.set()
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "terminada"))
        self.assertEqual(len(bajador.llamadas), 1)

    def test_cancelar_durante_descarga_da_cancelada(self):
        def _hacer(solicitud, progreso, cancelar, pausar):
            while not cancelar.wait(0.01):
                pass
            raise downloader.Cancelada()

        cola, _, _ = _nueva_cola(comportamiento=_hacer)
        ident = cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "descargando"))
        self.assertTrue(cola.cancelar(ident))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "cancelada"))
        self.assertIsNone(cola.items()[0].get("ruta"))

    def test_borrar_no_toca_los_activos_y_si_los_frenados(self):
        cola, _, _ = _nueva_cola()
        ident = cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "terminada"))
        # F5: "Quitar" en una terminada saca la fila (el archivo queda).
        self.assertTrue(cola.borrar(ident))
        self.assertEqual(len(cola.items()), 0)

        libre = threading.Event()
        cola2, bajador2, _ = _nueva_cola(comportamiento=_bloqueante(libre))
        cola2.agregar(dict(SNAPSHOT))                       # trabada acá
        self.assertTrue(_esperar(lambda: len(bajador2.llamadas) == 1))
        ident2 = cola2.agregar(dict(SNAPSHOT, titulo="2"))  # en espera seguro
        self.assertTrue(cola2.cancelar(ident2))
        self.assertTrue(cola2.borrar(ident2))
        self.assertEqual(len(cola2.items()), 1)
        libre.set()

    def test_borrar_no_saca_un_item_esperando(self):
        libre = threading.Event()
        cola, _, _ = _nueva_cola(comportamiento=_bloqueante(libre))
        cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "descargando"))
        ident = cola.agregar(dict(SNAPSHOT, titulo="ena"))
        self.assertFalse(cola.borrar(ident))
        self.assertEqual(len(cola.items()), 2)
        libre.set()

    def test_limpiar_saca_terminadas_y_canceladas(self):
        cola, _, _ = _nueva_cola()
        cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "terminada"))
        self.assertEqual(cola.limpiar(), 1)
        self.assertEqual(len(cola.items()), 0)
        self.assertEqual(cola.limpiar(), 0)      # sin nada, no avisa de más


class Pausar(unittest.TestCase):
    def test_pausar_en_espera_no_arranca_y_reanudar_vuelve(self):
        liberar = threading.Event()
        cola, bajador, _ = _nueva_cola(comportamiento=_bloqueante(liberar))
        cola.agregar(dict(SNAPSHOT))
        segundo = cola.agregar(dict(SNAPSHOT, titulo="2"))
        self.assertTrue(_esperar(lambda: len(bajador.llamadas) == 1))
        self.assertTrue(cola.pausar(segundo))
        self.assertEqual(cola.items()[1]["estado"], "pausa")
        self.assertEqual(len(bajador.llamadas), 1)
        self.assertTrue(cola.reanudar(segundo))
        self.assertEqual(cola.items()[1]["estado"], "espera")
        liberar.set()
        self.assertTrue(_esperar(lambda: cola.items()[1]["estado"]
                                 == "terminada"))
        self.assertEqual(len(bajador.llamadas), 2)

    def test_pausar_durante_descarga_conserva_parciales_y_cancelar_limpia(self):
        with tempfile.TemporaryDirectory() as carpeta:
            parcial = Path(carpeta) / "Me at the zoo.mp4.part"
            parcial.write_bytes(b"x" * 10)

            def _hacer(solicitud, progreso, cancelar, pausar):
                while not pausar.wait(0.01):
                    if cancelar.is_set():
                        raise downloader.Cancelada()
                raise downloader.Pausada([str(parcial)])

            cola, _, _ = _nueva_cola(comportamiento=_hacer)
            ident = cola.agregar(dict(SNAPSHOT))
            self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                     == "descargando"))
            self.assertTrue(cola.pausar(ident))
            self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                     == "pausa"))
            self.assertTrue(parcial.exists())   # .part conservado
            cola.cancelar(ident)                # cancelar desde pausa
            self.assertEqual(cola.items()[0]["estado"], "cancelada")
            self.assertFalse(parcial.exists())  # limpiado


class Reintentos(unittest.TestCase):
    def test_error_transitorio_reintenta_circular_y_termina(self):
        llamadas = []

        def _hacer(solicitud, progreso, cancelar, pausar):
            llamadas.append(1)
            if len(llamadas) == 1:
                raise ErrorMiauki("tiempo_agotado")
            return {"ruta": r"C:\dl\x.mp4"}

        cola, bajador, _ = _nueva_cola(comportamiento=_hacer)
        cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "terminada"))
        self.assertEqual(len(llamadas), 2)
        self.assertEqual(len(bajador.llamadas), 2)

    def test_error_permanente_no_reintenta(self):
        def _hacer(solicitud, progreso, cancelar, pausar):
            raise ErrorMiauki("video_eliminado")

        cola, bajador, _ = _nueva_cola(comportamiento=_hacer)
        ident = cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "error"))
        self.assertEqual(len(bajador.llamadas), 1)
        error = cola.items()[0]["error"]
        self.assertEqual(error["codigo"], "video_eliminado")
        self.assertIn("ya no existe", error["mensaje"])
        # reintentar a mano vuelve a probar (y vuelve a fallar acá)
        self.assertTrue(cola.reintentar(ident))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "error"))
        self.assertEqual(len(bajador.llamadas), 2)

    def test_los_reintentos_transitorios_se_agotan(self):
        def _hacer(solicitud, progreso, cancelar, pausar):
            raise ErrorMiauki("sin_internet")

        cola, bajador, _ = _nueva_cola(comportamiento=_hacer)
        cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"]
                                 == "error"))
        # 1 intento + 2 reintentos (decisión 3d.10)
        self.assertEqual(len(bajador.llamadas), 3)
        self.assertEqual(cola.items()[0]["error"]["codigo"], "sin_internet")

    def test_reintentar_refresca_el_selector(self):
        # Ajustes 21/11: reintentar reanaliza y actualiza el selector/calidad.
        def _hacer(solicitud, progreso, cancelar, pausar):
            raise ErrorMiauki("video_eliminado")

        def analizar(url, **kw):
            return {"calidades": [
                {"selector": "best[height<=1080]", "contenedor": "mp4",
                 "resolucion": 1080, "recomendada": None}]}

        cola, _, _ = _nueva_cola(comportamiento=_hacer, analizar=analizar)
        ident = cola.agregar(dict(SNAPSHOT, resolucion=1080))
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "error"))
        self.assertEqual(cola._buscar(ident)["selector"], "137+140")
        self.assertTrue(cola.reintentar(ident))
        self.assertEqual(cola._buscar(ident)["selector"], "best[height<=1080]")

    def test_reintentar_no_se_rompe_si_el_analisis_falla(self):
        def _hacer(solicitud, progreso, cancelar, pausar):
            raise ErrorMiauki("tiempo_agotado")

        def analizar(url, **kw):
            raise ErrorMiauki("tiempo_agotado")

        cola, _, _ = _nueva_cola(comportamiento=_hacer, analizar=analizar)
        ident = cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "error"))
        self.assertTrue(cola.reintentar(ident))
        # reintenta igual con lo que había: el descargador vuelve a probar
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "error"))


class PesoTotal(unittest.TestCase):
    """F5 B5: el peso real incluye el archivo y sus subtítulos hermanos."""

    def test_suma_el_archivo_y_sus_subs(self):
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta) / "video [1].mp4"
            base.write_bytes(b"x" * 1000)
            (Path(carpeta) / "video [1].es.srt").write_bytes(b"y" * 30)
            (Path(carpeta) / "video [1].en.vtt").write_bytes(b"z" * 20)
            # Ajeno: otro video que empieza parecido NO se suma.
            (Path(carpeta) / "video [1] extra.srt").write_bytes(b"w" * 500)
            self.assertEqual(queue_manager._peso_total(str(base)), 1050)

    def test_archivo_que_no_existe_da_cero(self):
        self.assertEqual(queue_manager._peso_total(r"C:\no\existe\x.mp4"), 0)


class ColaInterrumpida(unittest.TestCase):
    """F6 B3: lo no terminado se guarda y vuelve como "interrumpida"."""

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp(prefix="miauki_b3_"))
        self.ruta = self.carpeta / "cola.json"
        self.libertad = threading.Event()
        self.addCleanup(self.libertad.set)

    def _cola(self, comportamiento=None, ajustes=None, historial=None):
        reg = _Registrador()
        cola = queue_manager.Cola(
            bajar=_BajadorFalso(comportamiento or _bloqueante(self.libertad)),
            emitir=reg,
            ajustes=ajustes or {"carpeta_descargas": str(self.carpeta)},
            ruta_cola=self.ruta, historial=historial,
            analizar=lambda url, **kw: {})
        return cola, reg

    def _pendiente(self, cola):
        cola.agregar(dict(SNAPSHOT, resolucion=1080))
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "descargando"))

    def test_guarda_solo_lo_no_terminado_sin_miniatura(self):
        cola, _ = self._cola()
        self._pendiente(cola)
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(len(datos["items"]), 1)
        self.assertEqual(datos["items"][0]["estado"], "descargando")
        self.assertEqual(datos["items"][0]["miniatura"], "")
        self.libertad.set()
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "terminada"))
        self.assertEqual(json.loads(self.ruta.read_text(encoding="utf-8"))["items"], [])

    def test_cargar_los_deja_interrumpidos_sin_arrancar_solos(self):
        archivo = self.carpeta / "video.mp4"
        parcial = self.carpeta / "video.mp4.part"
        ajeno = self.carpeta / "otro.mp4.part"
        for f in (archivo, parcial, ajeno):
            f.write_bytes(b"x")
        self.ruta.write_text(json.dumps({"version": 1, "items": [dict(
            SNAPSHOT, id="a" * 32, resolucion=1080,
            parciales=[str(archivo)])]}), encoding="utf-8")
        cola, reg = self._cola()
        self.assertEqual(cola.cargar_pendientes(), 1)
        item = cola.items()[0]
        self.assertEqual(item["estado"], "interrumpida")
        self.assertFalse(parcial.exists(), "no se borró el .part del ítem")
        self.assertTrue(archivo.exists(), "se borró el archivo final")
        self.assertTrue(ajeno.exists(), "se borró el parcial de otro ítem")
        time.sleep(0.2)
        self.assertEqual(cola._bajar.llamadas if hasattr(cola._bajar, "llamadas") else [], [])
        self.assertIsNone(cola._hilo)

    def test_reintentar_y_quitar_aceptan_interrumpida(self):
        self.ruta.write_text(json.dumps({"version": 1, "items": [
            dict(SNAPSHOT, id="a" * 32)]}), encoding="utf-8")
        cola, _ = self._cola()
        cola.cargar_pendientes()
        self.assertTrue(cola.reintentar("a" * 32))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"] == "descargando"))
        self.libertad.set()
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"] == "terminada"))
        self.assertTrue(cola.borrar("a" * 32))

    def test_cierre_confirmado_cancela_y_no_deja_interrumpidas(self):
        cola, _ = self._cola()
        self._pendiente(cola)
        self.assertEqual(cola.cancelar_todo(), 1)
        self.assertEqual(cola.items()[0]["estado"], "cancelada")
        self.assertEqual(json.loads(self.ruta.read_text(encoding="utf-8"))["items"], [])

    def test_pausar_todo_y_luego_cancelar_todo_deja_canceladas_en_la_cola(self):
        # Ajustes 21/11 (repro): el botón global "Cancelar todo" no hacía
        # nada porque faltaba el método en el puente. Acá se prueba el flujo
        # completo en la Cola: pausar todo → cancelar todo → las filas quedan
        # como "cancelada" (sin borrarse) hasta el tacho.
        cola, _ = self._cola()
        ids = [cola.agregar(dict(SNAPSHOT, titulo="v%d" % i)) for i in range(3)]
        self.assertEqual(cola.pausar_todo(), 3)
        # Pausar una descarga YA arrancada es asincrónico (el trabajador
        # cambia a "pausa" cuando atiende la señal): se espera, no se lee al
        # instante, o el test falla según quién gane la carrera.
        self.assertTrue(_esperar(
            lambda: all(cola._buscar(i)["estado"] == "pausa" for i in ids)))
        self.assertEqual(cola.cancelar_todo(), 3)
        for ident in ids:
            item = cola._buscar(ident)
            self.assertIsNotNone(item)
            self.assertEqual(item["estado"], "cancelada")
        # El tacho recién acá las quita de la lista (no antes).
        self.assertEqual(cola.limpiar_historial(), 3)
        self.assertEqual([i for i in cola.items() if i["id"] in ids], [])

    def test_cola_rota_se_respalda_y_no_rompe_el_arranque(self):
        self.ruta.write_text("no soy json", encoding="utf-8")
        cola, _ = self._cola()
        self.assertEqual(cola.cargar_pendientes(), 0)
        self.assertEqual(len(list(self.carpeta.glob("cola.roto-*.json"))), 1)


class HistorialDeLaCola(unittest.TestCase):
    """F6 B1: solo se registra una descarga TERMINADA y si está encendido."""

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp(prefix="miauki_hist_cola_"))
        self.historial = history.Historial(self.carpeta / "historial.json")

    def _correr(self, guardar):
        reg = _Registrador()
        cola = queue_manager.Cola(
            bajar=_BajadorFalso(), emitir=reg,
            ajustes={"carpeta_descargas": str(self.carpeta),
                     "guardar_historial": guardar},
            ruta_cola=self.carpeta / "cola.json", historial=self.historial)
        cola.agregar(dict(SNAPSHOT, resolucion=1080))
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "terminada"))
        return cola, reg

    def test_registra_la_terminada_con_contenedor_real(self):
        cola, reg = self._correr(True)
        entradas = self.historial.listar()
        self.assertEqual(len(entradas), 1)
        self.assertEqual(entradas[0]["titulo"], "Me at the zoo")
        self.assertEqual(entradas[0]["contenedor"], "mp4")
        self.assertEqual(entradas[0]["calidad"], "1080p")
        self.assertEqual(entradas[0]["sitio"], "otro")
        self.assertEqual(reg.ultimo("historial"), {"cambio": True})
        # La Cola muestra formato y fecha/hora de la descarga terminada.
        item = cola.items()[0]
        self.assertEqual(item["contenedor"], "mp4")
        self.assertTrue(item["fecha"])

    def test_apagado_no_registra_nada(self):
        self._correr(False)
        self.assertEqual(self.historial.listar(), [])

    def test_playlist_registra_el_titulo_real(self):
        # Plan archivos y cola, paso 1: el historial guarda el título sin el
        # prefijo [Bloque X/Y] que solo se ve en la Cola.
        reg = _Registrador()
        cola = queue_manager.Cola(
            bajar=_BajadorFalso(), emitir=reg,
            ajustes={"carpeta_descargas": str(self.carpeta),
                     "guardar_historial": True},
            ruta_cola=self.carpeta / "cola.json", historial=self.historial)
        cola.agregar_playlist(dict(
            SNAPSHOT, titulo="Lista",
            entradas=[dict(SNAPSHOT, titulo="Video 1")]))
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "terminada"))
        self.assertEqual(self.historial.listar()[0]["titulo"], "Video 1")

    def test_si_el_historial_no_se_puede_escribir_la_descarga_queda_ok(self):
        """Disco lleno / archivo bloqueado: la descarga terminó y no se pierde."""
        class _HistorialRoto:
            def agregar(self, datos):
                raise OSError("sin espacio")

        reg = _Registrador()
        cola = queue_manager.Cola(
            bajar=_BajadorFalso(), emitir=reg,
            ajustes={"carpeta_descargas": str(self.carpeta),
                     "guardar_historial": True},
            ruta_cola=self.carpeta / "cola.json", historial=_HistorialRoto())
        cola.agregar(dict(SNAPSHOT, resolucion=1080))
        self.assertTrue(_esperar(
            lambda: cola.items()[0]["estado"] == "terminada"))
        self.assertEqual(reg.ultimo("historial"), None)

    def test_una_cancelada_no_se_registra(self):
        libertad = threading.Event()
        reg = _Registrador()
        cola = queue_manager.Cola(
            bajar=_BajadorFalso(_bloqueante(libertad)), emitir=reg,
            ajustes={"carpeta_descargas": str(self.carpeta),
                     "guardar_historial": True},
            ruta_cola=self.carpeta / "cola.json", historial=self.historial)
        cola.agregar(dict(SNAPSHOT))
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"] == "descargando"))
        cola.cancelar(cola.items()[0]["id"])
        self.assertTrue(_esperar(lambda: cola.items()[0]["estado"] == "cancelada"))
        self.assertEqual(self.historial.listar(), [])


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Miauki YT v1.0 — punto de entrada.

Uso:
  python app.py                 abre la ventana
  python app.py --selftest      verifica ffmpeg, yt-dlp, carpetas, WebView2 e interfaz
  python app.py --version      imprime la versión y sale
"""
import atexit
import ctypes
from ctypes import wintypes
import faulthandler
import os
import sys
import tempfile
import threading
import time

from miauki import app_info, paths
from miauki.core import assets_check, procesos, webview2
from miauki.core import ventana as ventana_so
from miauki.core.ffmpeg_tools import verificar_ffmpeg
from miauki.core.logger import obtener_logger

_MUTEX = None


def instancia_unica() -> bool:
    """True si esta es la única instancia (mutex con nombre en Windows)."""
    global _MUTEX
    kernel32 = ctypes.windll.kernel32
    kernel32.SetLastError(0)
    _MUTEX = kernel32.CreateMutexW(None, False, "MiaukiYT_v1_unica")
    return kernel32.GetLastError() != 183  # 183 = ERROR_ALREADY_EXISTS


def dialogo_error(texto: str) -> None:
    """Cuadro de mensaje de Windows (user32, sin shell)."""
    user32 = ctypes.windll.user32
    user32.MessageBoxW(None, texto, app_info.NOMBRE, 0x10)  # 0x10 = MB_ICONERROR


def _instrumentar_salida(log) -> None:
    """Rastro de por qué murió o salió el proceso (0.1 estabilidad).

    Evidencia que distingue los casos:
      - salida normal: las últimas líneas del log son "finaliza con código N";
      - crash nativo (Access Violation): faulthandler escribe la pila en faults.log;
      - excepción no capturada: excepthook la registra con su causa;
      - hilo con excepción: threading.excepthook la registra por nombre de hilo.
    """
    try:
        f = open(paths.dir_logs() / "faults.log", "a", encoding="utf-8", buffering=1)
        faulthandler.enable(f, all_threads=True)
    except Exception:
        log.warning("No se pudo activar faulthandler")

    def _excepcion_no_capturada(tipo, valor, tb):
        log.error("Excepción no capturada: %s", valor, exc_info=(tipo, valor, tb))

    def _excepcion_en_hilo(args):
        log.error("Excepción no capturada en hilo %r: %s", args.thread.name, args.exc_value,
                  exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = _excepcion_no_capturada
    threading.excepthook = _excepcion_en_hilo
    atexit.register(lambda: log.info("Fin de atexit: el proceso salió de Python sin crash nativo"))


def selftest() -> int:
    """Chequeos del esqueleto. Sale con 0 si todo está bien."""
    resultados: list[tuple[bool, str]] = []

    ok, msg = verificar_ffmpeg(paths.ruta_ffmpeg())
    resultados.append((ok, f"ffmpeg: {msg}"))

    try:
        from miauki.core import motor
        v = motor.ytdlp().version.__version__
        resultados.append((True, f"yt-dlp: {v} ({motor.origen_en_uso()}, {motor.version_en_uso()})"))
    except Exception as e:
        resultados.append((False, f"yt-dlp: no se pudo importar ({e})"))

    try:
        d = paths.dir_datos()
        with tempfile.NamedTemporaryFile(dir=d, delete=True):
            pass
        resultados.append((True, f"carpeta de datos: {d} (escribible)"))
    except Exception as e:
        resultados.append((False, f"carpeta de datos: no se pudo usar ({e})"))

    ok, msg = webview2.instalado()
    resultados.append((ok, f"WebView2: {msg}"))

    ruta, fuente = paths.fuente_interfaz()
    resultados.append((ruta.is_file(), f"interfaz {fuente}: {ruta}"))

    ok, msg = assets_check.verificar_assets()
    resultados.append((ok, f"lista negra de assets: {msg}"))

    log = obtener_logger()
    fallos = 0
    for ok, msg in resultados:
        marca = "OK  " if ok else "FALLO"
        print(f"[{marca}] {msg}")
        log.info("selftest [%s] %s", marca.strip(), msg)
        fallos += 0 if ok else 1

    if fallos:
        print(f"\n{fallos} chequeo(s) fallaron.", file=sys.stderr)
        return 1
    print("\nTodos los chequeos pasaron.")
    return 0


def _consola_si_hace_falta() -> None:
    """El .exe va sin consola (--windowed); para --selftest/--version la abrimos."""
    if paths.congelado() and sys.stdout is None:
        kernel32 = ctypes.windll.kernel32
        kernel32.AllocConsole()
        sys.stdout = open("CONOUT$", "w", encoding="utf-8")
        sys.stderr = sys.stdout


def _tope_util(ancho: int, alto: int, util_w: int, util_h: int, factor: float = 0.85) -> tuple[int, int]:
    """El 85% del área útil como máximo por dimensión."""
    return min(ancho, int(util_w * factor)), min(alto, int(util_h * factor))


def _tamano_ventana(ancho: int = 1420, alto: int = 840) -> tuple[int, int]:
    """Tamaño inicial de la ventana (1420×840); en pantallas chicas no supera el 85% del área útil."""
    try:
        rect = wintypes.RECT()
        # SPI_GETWORKAREA (48): recta del área de trabajo del monitor primario
        if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
            ancho, alto = _tope_util(ancho, alto, rect.right - rect.left, rect.bottom - rect.top)
    except Exception:
        pass  # sin área útil medible: se abre en 1200×720
    return ancho, alto


def _instrumentar_webview(ventana, log) -> None:
    """ProcessFailed de WebView2: NO se engancha.

    Se probó (2026-10-20): acceder a `ventana.native.browser.webview.CoreWebView2`
    o suscribirse a su evento `ProcessFailed` desde el evento `loaded` de
    pywebview deja la interfaz congelada; la ventana deja de responder incluso
    a WM_CLOSE (probado en ventana real: con el enganche, la app no cierra; sin
    él, cierra con código 0). pywebview 6.2.1 no lo expone en su API.
    Queda pendiente para Fase 8 con una vía que no bloquee el hilo de la UI
    (docs/PENDIENTES.md).
    """
    log.info("ProcessFailed de WebView2 no accesible sin colgar la interfaz")


def main() -> int:
    # Todo proceso deja rastro en el log, incluso si sale antes de abrir la ventana
    log = obtener_logger()
    _instrumentar_salida(log)
    inicio = time.monotonic()
    log.info("Proceso iniciado (pid %s, args=%s)", os.getpid(), sys.argv[1:])

    if "--version" in sys.argv or "--selftest" in sys.argv:
        _consola_si_hace_falta()

    if "--version" in sys.argv:
        print(app_info.VERSION)
        return 0

    if "--probar-motor" in sys.argv:
        _consola_si_hace_falta()
        from miauki.core import motor
        i = sys.argv.index("--probar-motor")
        if i + 1 >= len(sys.argv):
            print("Falta la carpeta del motor")
            return 1
        return motor.probar_motor(sys.argv[i + 1], sys.argv[i + 2] if i + 2 < len(sys.argv) else "")

    if "--selftest" in sys.argv:
        return selftest()

    if not instancia_unica():
        log.info("Otra instancia ya está corriendo: este proceso sale sin abrir ventana.")
        print(f"{app_info.NOMBRE} ya está corriendo.")
        return 0

    ok, msg = webview2.garantizar()  # flujo B: si falta WebView2, se instala solo
    if not ok:
        log.error("WebView2 no disponible: %s", msg)
        dialogo_error(msg)
        return 1

    procesos.atar()  # los renderers de WebView2 mueren con este proceso

    ruta, fuente = paths.fuente_interfaz()
    if not ruta.is_file():
        log.error("Falta la interfaz: %s", ruta)
        print(f"Falta la interfaz: {ruta}", file=sys.stderr)
        return 1
    log.info("Arranque de %s %s (interfaz %s, congelado=%s)",
             app_info.NOMBRE, app_info.VERSION, fuente, paths.congelado())

    import webview

    from miauki import events
    from miauki.api import Api
    from miauki.core import queue_manager

    cola = queue_manager.obtener()
    n_pendientes = cola.cargar_pendientes()   # F6 B3: nunca se reanudan solos
    if n_pendientes:
        log.info("Cola con %s descargas interrumpidas del cierre anterior", n_pendientes)
    ancho, alto = _tamano_ventana()
    log.info("Tamaño inicial de ventana: %sx%s", ancho, alto)
    ventana = webview.create_window(
        app_info.NOMBRE,
        # Ruta plain (sin file://): pywebview levanta su servidor interno que
        # escucha SOLO en 127.0.0.1 y sirve SOLO la carpeta de la interfaz
        # (ver docs/DECISIONES.md, sección de seguridad del servidor)
        url=str(ruta),
        js_api=Api(cola=cola),
        width=ancho,
        height=alto,
        min_size=(880, 560),
        resizable=True,
    )

    def al_cerrar():
        """Pide confirmación si quedan descargas en curso. Devolver False
        cancela el cierre (convención de pywebview)."""
        n = cola.activos()
        # "quién lo originó": pywebview no lo dice; lo que sí se puede afirmar
        # es que el cierre entró por su evento (usuario, Alt+F4 o destroy) y
        # si hubo que confirmar. Un cierre sin este evento es un cierre raro.
        log.info("Evento closing (hilo %s, pid %s, activos=%s)",
                 threading.current_thread().name, os.getpid(), n)
        if n <= 0:
            return True
        plural = "descarga" if n == 1 else "descargas"
        texto = (f"Hay {n} {plural} en curso. Si cerrás ahora, se cancelan."
                 "\n\n¿Cerrar igual?")
        try:
            permitir = bool(ventana.create_confirmation_dialog("Cerrar Miauki YT", texto))
        except Exception:
            log.warning("No se pudo mostrar la confirmación de cierre", exc_info=True)
            permitir = True
        log.info("Confirmación de cierre: %s", "cerrar" if permitir else "cancelar")
        if permitir:
            # Lo cancelado al cerrar no debe volver como "interrumpida" (B3).
            cola.cancelar_todo()
        return permitir

    def al_cerrar_del_todo():
        log.info("Evento closed: la ventana se destruyó (pid %s)", os.getpid())

    ventana.events.closing += al_cerrar
    ventana.events.closed += al_cerrar_del_todo
    _instrumentar_webview(ventana, log)
    events.conectar(ventana)
    # B3: parpadeo en la barra de tareas cuando una descarga termina y la
    # ventana no está al frente (sin sonido, no molesta si ya estás ahí).
    events.suscribir(
        ventana_so.AvisosDeFin(
            lambda: ventana_so.hwnd_propio(app_info.NOMBRE)).al_evento)

    def al_cargar():
        """Con la ventana lista: comprobar el motor en segundo plano (A5)."""
        try:
            from miauki.core import actualizador
            actualizador.comprobar_en_segundo_plano()
        except Exception:
            log.warning("No se pudo lanzar la comprobación del motor", exc_info=True)

    ventana.events.loaded += al_cargar
    # Perfil propio: pywebview en modo privado usaría %TEMP%\tmpXXXX y lo
    # dejaría tirado si el proceso muere. Con storage_path la carpeta es
    # nuestra y demostrable; en modo privado se borra al cerrar bien.
    webview.start(gui="edgechromium", private_mode=True,
                  storage_path=str(paths.dir_perfil_webview()))
    log.info("webview.start volvió tras %.1f s: el bucle de la interfaz terminó",
             time.monotonic() - inicio)
    return 0


if __name__ == "__main__":
    try:
        _codigo = main()
    except BaseException as _exc:
        obtener_logger().error("main() terminó con excepción: %r", _exc, exc_info=True)
        _codigo = 1
    obtener_logger().info("Proceso finaliza con código %s", _codigo)
    sys.exit(_codigo)

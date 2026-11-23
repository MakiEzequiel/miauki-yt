# -*- coding: utf-8 -*-
"""Cola de descargas: máquina de estados (spec §4, decisiones §3d).

Estados: espera → descargando → procesando → terminada | error | cancelada
+ pausa (entrada desde espera/descargando, salida a espera). 10 en espera
como máximo y 1 activa a la vez; el ítem corre en un hilo único que llama
a downloader.descargar con sus eventos cancelar/pausar.

Eventos hacia la interfaz (3d.11): "cola" (lista completa, en cada cambio)
y "progreso" (máx ~4/s, ya filtrado por el descargador). El hilo del
trabajador nace y muere solo: cuando no queda nada en espera sale; agregar
o reanudar lo vuelve a arrancar.
"""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from miauki import events, paths
from miauki.core import analyzer, downloader, errors, history, settings, validacion
from miauki.core.errors import ErrorMiauki
from miauki.core.logger import obtener_logger

MAX_ACTIVAS = 1          # spec §4: 1 activa a la vez (un solo trabajador)
MAX_ESPERA = 10          # spec §4: hasta 10 en espera + 1 activa
REINTENTOS = 2           # decisión 3d.10: 2 reintentos circulares
EN_CURSO = ("espera", "descargando", "procesando", "pausa")
TRANSITORIOS = {"sin_internet", "tiempo_agotado", "error_desconocido",
                "calidad_no_disponible", "sin_subtitulos"}
BORRABLES = ("terminada", "error", "cancelada", "interrumpida")
LIMPIABLES = ("terminada", "cancelada")
# Lo que se guarda en cola.json: lo que no llegó a terminar. Una descarga con
# error o cancelada ya tuvo su final y no se resucita como interrumpida.
PERSISTIBLES = ("espera", "descargando", "procesando", "pausa", "interrumpida")
_SUBS = (".srt", ".vtt", ".ass")
NOMBRE_COLA = "cola.json"


def _peso_total(ruta: str) -> int:
    """Tamaño real descargado: el archivo más sus subtítulos hermanos (F5 B5).

    Se compara por prefijo de nombre, sin `glob`, porque un título puede traer
    corchetes y glob los leería como comodines.
    """
    try:
        base = Path(ruta)
        total = base.stat().st_size
        for hermano in base.parent.iterdir():
            if (hermano != base and hermano.suffix.lower() in _SUBS
                    and hermano.name.startswith(base.stem + ".")):
                total += hermano.stat().st_size
    except OSError:
        return 0
    return total


def _entrada_historial(item: dict, ruta: str, peso: int) -> dict:
    """Datos de una descarga terminada para el historial (Fase 6)."""
    tipo = item.get("tipo") or "video"
    if tipo == "video":
        calidad = f"{item['resolucion']}p" if item.get("resolucion") else ""
    elif tipo == "musica":
        calidad = f"{item['kbps']} kbps" if item.get("kbps") else ""
    else:
        calidad = "Foto"
    return {
        "titulo": (item.get("_titulo_real") or item.get("titulo")
                   or Path(ruta).stem),
        "sitio": item.get("sitio") or "otro",
        "tipo": tipo,
        "calidad": calidad,
        "contenedor": Path(ruta).suffix.lstrip(".").lower(),
        "ruta": ruta,
        "peso": peso,
        "url_canonica": item.get("url_canonica") or "",
        "miniatura": item.get("miniatura") or "",
        "selector": item.get("selector") or "",
        "resolucion": item.get("resolucion"),
        "kbps": item.get("kbps"),
        "con_subs": bool(item.get("con_subs")),
    }


class Cola:
    """La máquina de estados. `bajar` y `emitir` se inyectan en los tests."""

    def __init__(self, bajar=None, emitir=None, ajustes=None, ruta_cola=None,
                 historial=None, analizar=None):
        self._bajar = bajar or downloader.descargar
        self._emitir = emitir or events.emitir
        self._ajustes = ajustes            # None → settings.cargar() al correr
        self._historial = historial        # None → history.obtener()
        self._analizar = analizar or analyzer.analizar
        self._ruta_cola = Path(ruta_cola) if ruta_cola else (paths.dir_datos() / NOMBRE_COLA)
        self._items: list[dict] = []
        self._traba = threading.RLock()
        self._hilo = None
        self._senales: dict[str, tuple[threading.Event, threading.Event]] = {}

    # ---------- consultas ----------

    def items(self) -> list[dict]:
        """Copia pública de los ítems (sin claves internas _x)."""
        with self._traba:
            return [self._publico(i) for i in self._items]

    def _publico(self, item: dict) -> dict:
        publico = {k: v for k, v in item.items() if not k.startswith("_")}
        # Bloque de playlist (plan ajustes UI): la interfaz lo muestra en la fila.
        if item.get("_bloque_total"):
            publico["bloque"] = "%d/%d" % (item["_bloque_num"],
                                           item["_bloque_total"])
        return publico

    def _buscar(self, ident) -> dict | None:
        return next((i for i in self._items if i["id"] == ident), None)

    def _en_espera(self) -> int:
        return sum(1 for i in self._items if i["estado"] == "espera")

    def activos(self) -> int:
        """Ítems que siguen en curso (espera/descargando/procesando/pausa).
        La interfaz lo usa para avisar antes de cerrar la app."""
        with self._traba:
            return sum(1 for i in self._items if i["estado"] in EN_CURSO)

    def _avisar_cola(self):     # bajo self._traba (RLock)
        copia = [self._publico(i) for i in self._items]
        self._persistir()
        self._emitir("cola", copia)

    def _persistir(self):       # bajo self._traba
        """Guarda en cola.json solo lo que no terminó (Fase 6, B3)."""
        pendientes = []
        for item in self._items:
            if item["estado"] not in PERSISTIBLES:
                continue
            guardado = {k: v for k, v in self._publico(item).items()
                        if k in ("id", "titulo", "sitio", "tipo", "selector",
                                 "contenedor", "kbps", "resolucion", "con_subs",
                                 "url_canonica", "estado", "peso")}
            guardado["miniatura"] = ""      # snapshot liviano: sin data URI
            guardado["parciales"] = [n for n in item.get("_parciales", [])
                                     if isinstance(n, str)]
            pendientes.append(guardado)
        try:
            temporal = self._ruta_cola.with_name(self._ruta_cola.name + ".tmp")
            temporal.write_text(
                json.dumps({"version": 1, "items": pendientes}, ensure_ascii=False),
                encoding="utf-8")
            os.replace(temporal, self._ruta_cola)
        except OSError:
            obtener_logger().warning("No se pudo guardar la cola interrumpida")

    def cargar_pendientes(self) -> int:
        """Recupera los ítems que quedaron sin terminar tras un cierre brusco.

        Quedan como "interrumpida" con Reintentar/Quitar: NUNCA se reanudan
        solos. Borra únicamente los temporales que el propio yt-dlp nombró
        para esos ítems (nunca otros archivos de la carpeta).
        """
        with self._traba:
            if not self._ruta_cola.is_file():
                return 0
            try:
                datos = json.loads(self._ruta_cola.read_text(encoding="utf-8"))
                brutos = datos.get("items") if isinstance(datos, dict) else None
                if not isinstance(brutos, list):
                    raise ValueError("formato desconocido")
            except (OSError, ValueError):
                respaldo = self._ruta_cola.with_name(
                    f"cola.roto-{uuid.uuid4().hex[:8]}.json")
                try:
                    os.replace(self._ruta_cola, respaldo)
                except OSError:
                    pass
                obtener_logger().warning("Cola interrumpida ilegible: se empieza sin ítems")
                return 0
            recuperados = 0
            vistos = set()
            for bruto in brutos:
                try:
                    item = validacion.snapshot_limpio(bruto)
                except ErrorMiauki:
                    continue
                ident = bruto.get("id")
                if not isinstance(ident, str) or len(ident) != 32 or ident in vistos:
                    ident = uuid.uuid4().hex
                vistos.add(ident)
                item["id"] = ident
                item["estado"] = "interrumpida"
                item["_intentos"] = 0
                item["miniatura"] = ""
                parciales = [n for n in (bruto.get("parciales") or [])
                             if isinstance(n, str)]
                self._items.append(item)
                downloader.limpiar_parciales(parciales)
                recuperados += 1
            if recuperados:
                obtener_logger().info("Cola: %s descarga(s) interrumpida(s) recuperadas",
                                      recuperados)
                self._avisar_cola()
            return recuperados

    def _arrancar_hilo(self):   # bajo self._traba
        if self._hilo is None or not self._hilo.is_alive():
            self._hilo = threading.Thread(target=self._correr,
                                          name="miauki-cola", daemon=True)
            self._hilo.start()

    # ---------- acciones de la interfaz ----------

    def agregar(self, snapshot: dict) -> str:
        """Encola el snapshot completo (decisión 3d.4) y devuelve su id."""
        with self._traba:
            if self._en_espera() >= MAX_ESPERA:
                raise ErrorMiauki("cola_llena")
            item = dict(snapshot)
            item["id"] = uuid.uuid4().hex
            item["estado"] = "espera"
            item["_intentos"] = 0
            self._items.append(item)
            self._avisar_cola()
            self._arrancar_hilo()
            return item["id"]

    def agregar_playlist(self, snapshot: dict) -> list[str]:
        """Encola cada video de una playlist (Paso 4) y devuelve sus ids.

        Una playlist no compite con el tope MAX_ESPERA de descargas sueltas
        (protege el abuso de la interfaz, no al usuario que ya eligió la
        lista); el trabajador único sigue garantizando MAX_ACTIVAS = 1.
        Listas grandes van en bloques de TAM_BLOQUE (plan ajustes UI): cada
        ítem muestra "[Bloque X/Y] [N/T]" en su título.
        """
        with self._traba:
            entradas = snapshot.get("entradas")
            if not isinstance(entradas, list) or not entradas:
                raise ErrorMiauki("playlist_sin_entradas")
            if len(entradas) > validacion.MAX_PLAYLIST:
                raise ErrorMiauki("playlist_muy_larga")
            total = len(entradas)
            total_bloques = (total + validacion.TAM_BLOQUE - 1) \
                // validacion.TAM_BLOQUE
            ids = []
            n = 0
            for bloque in range(total_bloques):
                inicio = bloque * validacion.TAM_BLOQUE
                for entrada in entradas[inicio:inicio + validacion.TAM_BLOQUE]:
                    if not isinstance(entrada, dict):
                        continue
                    n += 1
                    item = dict(entrada)
                    real = item.get("titulo") or ""
                    # Título real para el archivo y el historial (plan archivos
                    # y cola); el prefijo [Bloque X/Y] queda solo en la Cola.
                    item["_titulo_real"] = real
                    item["titulo"] = (f"[Bloque {bloque + 1}/{total_bloques}] "
                                      f"[{n}/{total}] {real}").strip()
                    item["id"] = uuid.uuid4().hex
                    item["estado"] = "espera"
                    item["_intentos"] = 0
                    item["_bloque_num"] = bloque + 1
                    item["_bloque_total"] = total_bloques
                    self._items.append(item)
                    ids.append(item["id"])
            if not ids:
                raise ErrorMiauki("playlist_sin_entradas")
            self._avisar_cola()
            self._arrancar_hilo()
            return ids

    def pausar(self, ident) -> bool:
        """Espera→pausa directa; descargando→señal (conserva .part, 3d.8)."""
        with self._traba:
            item = self._buscar(ident)
            if item is None:
                return False
            if item["estado"] == "espera":
                item["estado"] = "pausa"
                self._avisar_cola()
                return True
            if item["estado"] == "descargando":
                senales = self._senales.get(ident)
                if senales:
                    senales[1].set()
                    return True
            return False    # procesando no se pausa (3d.8); el resto no aplica

    def reanudar(self, ident) -> bool:
        with self._traba:
            item = self._buscar(ident)
            if item is None or item["estado"] != "pausa":
                return False
            if self._en_espera() >= MAX_ESPERA:
                raise ErrorMiauki("cola_llena")
            item["estado"] = "espera"
            self._avisar_cola()
            self._arrancar_hilo()
            return True

    def cancelar(self, ident) -> bool:
        with self._traba:
            item = self._buscar(ident)
            if item is None:
                return False
            estado = item["estado"]
            if estado == "espera":
                item["estado"] = "cancelada"
                self._avisar_cola()
                return True
            if estado == "pausa":
                item["estado"] = "cancelada"
                downloader.limpiar(item.pop("_parciales", []))
                self._avisar_cola()
                return True
            if estado in ("descargando", "procesando"):
                senales = self._senales.get(ident)
                if senales:
                    senales[0].set()
                    return True
            return False

    def cancelar_todo(self) -> int:
        """El usuario confirmó cerrar: cancela lo activo y vacía cola.json.

        Lo que se cancela al cerrar NO debe reaparecer como "interrumpida".
        Devuelve cuántos ítems se cancelaron.
        """
        with self._traba:
            n = 0
            for item in self._items:
                if item["estado"] in EN_CURSO:
                    item["estado"] = "cancelada"
                    downloader.limpiar(item.pop("_parciales", []))
                    senales = self._senales.get(item["id"])
                    if senales:
                        senales[0].set()
                    n += 1
            self._avisar_cola()
            return n

    def pausar_todo(self) -> int:
        """Pausa todas las activas (plan archivos y cola): espera va directo
        a pausa y descargando por señal (conserva .part). Procesando no se
        pausa (3d.8). Devuelve cuántas pausó."""
        with self._traba:
            n = 0
            for item in self._items:
                if item["estado"] == "espera":
                    item["estado"] = "pausa"
                    n += 1
                elif item["estado"] == "descargando":
                    senales = self._senales.get(item["id"])
                    if senales:
                        senales[1].set()
                        n += 1
            if n:
                self._avisar_cola()
            return n

    def reanudar_todo(self) -> int:
        """Vuelve todas las pausadas a la espera y arranca el trabajador.
        Sin tope MAX_ESPERA: igual que las playlists, el usuario ya eligió.
        Devuelve cuántas reanudó."""
        with self._traba:
            n = 0
            for item in self._items:
                if item["estado"] == "pausa":
                    item["estado"] = "espera"
                    n += 1
            if n:
                self._avisar_cola()
                self._arrancar_hilo()
            return n

    def limpiar_historial(self) -> int:
        """Tacho (plan archivos y cola): quita TODAS las filas terminadas,
        canceladas, con error e interrumpidas. Los archivos en disco NO se
        tocan. La interfaz lo habilita solo sin descargas activas."""
        with self._traba:
            antes = len(self._items)
            self._items = [i for i in self._items
                           if i["estado"] not in BORRABLES]
            quitados = antes - len(self._items)
            if quitados:
                self._avisar_cola()
            return quitados

    def borrar(self, ident) -> bool:
        """Quita de la lista un ítem que ya no está trabajando.

        La interfaz ofrece "Quitar" en terminadas, con error, canceladas e
        interrumpidas; un ítem activo primero se cancela.
        El archivo descargado NO se toca: solo se saca la fila.
        """
        with self._traba:
            item = self._buscar(ident)
            if item is None or item["estado"] not in BORRABLES:
                return False
            self._items.remove(item)
            self._senales.pop(ident, None)
            self._avisar_cola()
            return True

    def limpiar(self) -> int:
        """Quita de la lista todas las terminadas y canceladas. Devuelve cuántas."""
        with self._traba:
            antes = len(self._items)
            self._items = [i for i in self._items
                           if i["estado"] not in LIMPIABLES]
            quitados = antes - len(self._items)
            if quitados:
                self._avisar_cola()
            return quitados

    def reintentar(self, ident) -> bool:
        """Reintento circular a mano (3d.10): error/interrumpida→espera.

        Ajustes 21/11: antes de reencolar se limpian los temporales viejos y
        se refresca el análisis, para que el reintento no arrastre un formato
        o una calidad obsoleta (el botón "Probar de nuevo").
        """
        with self._traba:
            item = self._buscar(ident)
            if item is None or item["estado"] not in ("error", "interrumpida"):
                return False
            if self._en_espera() >= MAX_ESPERA:
                raise ErrorMiauki("cola_llena")
            downloader.limpiar_parciales(item.pop("_parciales", []))
        # Fuera del candado: el reanálisis puede tardar y no debe congelar
        # pausar/cancelar (ajustes 21/11).
        self._refrescar_item(item)
        with self._traba:
            item = self._buscar(ident)
            if item is None or item["estado"] not in ("error", "interrumpida"):
                return False
            if self._en_espera() >= MAX_ESPERA:
                raise ErrorMiauki("cola_llena")
            item.pop("error", None)
            item["_intentos"] = 0
            item["estado"] = "espera"
            self._mover_al_final(item)
            self._avisar_cola()
            self._arrancar_hilo()
            return True

    def _refrescar_item(self, item):
        """Actualiza selector/calidad del ítem con un análisis fresco y silencioso.

        Si el reanálisis falla o no hay con qué actualizar, el ítem queda
        como estaba (el descargador ya tiene su red de seguridad).
        """
        try:
            res = self._analizar(item.get("url_canonica") or "", forzar=True)
        except Exception:
            return
        tipo = item.get("tipo")
        if tipo == "musica":
            musica = res.get("musica") or []
            if musica:
                item["selector"] = "bestaudio"
                if musica[0].get("kbps"):
                    item["kbps"] = musica[0]["kbps"]
            return
        if tipo != "video":
            return
        calidades = res.get("calidades") or []
        if not calidades:
            return
        altura = item.get("resolucion")
        elegida = None
        if isinstance(altura, int):
            iguales = [c for c in calidades if c.get("resolucion") == altura]
            if iguales:
                elegida = iguales[0]
            else:
                menores = [c for c in calidades
                           if (c.get("resolucion") or 0) <= altura]
                if menores:
                    elegida = max(menores,
                                  key=lambda c: c.get("resolucion") or 0)
        if elegida is None:
            elegida = next((c for c in calidades if c.get("recomendada")),
                           calidades[0])
        if elegida.get("selector"):
            item["selector"] = elegida["selector"]
        if elegida.get("contenedor"):
            item["contenedor"] = elegida["contenedor"]

    # ---------- trabajador (1 hilo) ----------

    def _mover_al_final(self, item):    # bajo self._traba
        self._items.remove(item)
        self._items.append(item)

    def _correr(self):
        # Un único hilo trabajador => MAX_ACTIVAS (1) a la vez: toma un ítem,
        # lo baja de punta a punta y recién ahí busca el siguiente.
        while True:
            with self._traba:
                item = next((i for i in self._items
                             if i["estado"] == "espera"), None)
                if item is None:
                    self._hilo = None
                    return
                # las señales se registran ANTES de publicar "descargando"
                # para que pausar/cancelar nunca vean el estado sin señales
                cancelar = threading.Event()
                pausar = threading.Event()
                self._senales[item["id"]] = (cancelar, pausar)
                item["estado"] = "descargando"
                self._avisar_cola()
            self._bajar_item(item, cancelar, pausar)

    def _bajar_item(self, item, cancelar, pausar):
        ident = item["id"]

        def progreso(datos):
            parcial = datos.get("parcial")
            with self._traba:
                if isinstance(parcial, str) and parcial:
                    vistos = item.setdefault("_parciales", [])
                    if parcial not in vistos:
                        vistos.append(parcial)
                        self._persistir()   # si se corta la luz, sabemos qué borrar
                if datos.get("fase") == "proceso" and \
                        item["estado"] == "descargando":
                    item["estado"] = "procesando"
                    self._avisar_cola()
            self._emitir("progreso", dict(datos, id=ident))

        ajustes = self._ajustes if self._ajustes is not None \
            else settings.cargar()
        try:
            resultado = self._bajar(item, ajustes, progreso=progreso,
                                    cancelar=cancelar, pausar=pausar)
            with self._traba:
                item.pop("_parciales", None)
                item["ruta"] = resultado["ruta"]
                item["peso"] = _peso_total(resultado["ruta"])
                # Formato real del archivo y cuándo terminó: la Cola los
                # muestra junto al peso y el sitio de origen.
                item["contenedor"] = Path(resultado["ruta"]).suffix.lstrip(".").lower()
                item["fecha"] = datetime.now(timezone.utc).isoformat()
                entrada = _entrada_historial(item, item["ruta"], item["peso"])
            # El historial se escribe ANTES de publicar "terminada" (0.2): así
            # quien vea la fila terminada ya puede leer el historial, sin carrera.
            guardado = False
            if ajustes.get("guardar_historial") is True:
                try:
                    (self._historial or history.obtener()).agregar(entrada)
                    guardado = True
                except OSError:
                    # La descarga ya terminó: si el historial no se puede
                    # escribir (disco lleno, archivo bloqueado) no se pierde
                    # el archivo ni se marca la descarga como fallida.
                    obtener_logger().warning("Historial: no se pudo guardar")
            with self._traba:
                item["estado"] = "terminada"
                self._avisar_cola()
            if guardado:
                # La pantalla Historial se actualiza al instante si está abierta.
                self._emitir("historial", {"cambio": True})
        except downloader.Cancelada:
            with self._traba:
                item["estado"] = "cancelada"
                self._avisar_cola()
        except downloader.Pausada as exc:
            with self._traba:
                item["_parciales"] = list(exc.vistos)
                item["estado"] = "pausa"
                self._avisar_cola()
        except ErrorMiauki as exc:
            self._fallo(item, exc)
        except Exception:
            obtener_logger().exception("La cola atrapó un error inesperado")
            self._fallo(item, ErrorMiauki("error_desconocido"))
        finally:
            with self._traba:
                self._senales.pop(ident, None)

    def _fallo(self, item, exc: ErrorMiauki):
        with self._traba:
            reintentar = (exc.codigo in TRANSITORIOS
                          and item["_intentos"] < REINTENTOS
                          and self._en_espera() < MAX_ESPERA)
            if reintentar:
                item["_intentos"] += 1
                item["estado"] = "espera"
                self._mover_al_final(item)
            else:
                item["error"] = {"codigo": exc.codigo,
                                 "mensaje": exc.mensaje}
                item["estado"] = "error"
            self._avisar_cola()


_cola = Cola()


def obtener() -> Cola:
    """La instancia única de la app (la misma que usa api)."""
    return _cola

# -*- coding: utf-8 -*-
"""El puente: funciones que la interfaz puede pedirle a Python.

La interfaz llama a `pywebview.api.<metodo>()` (doc oficial: js_api).
Cada método validado en el borde y SIEMPRE devuelve {ok, data|error};
ninguna excepción llega a la interfaz: se registra en el log y se
devuelve un error amable.

Contrato de error (único en todos los métodos, §7):
    {"ok": false, "error": {"codigo": <código>, "mensaje": <español amable>}}
`codigo` es para que la interfaz pueda reaccionar; `mensaje` es lo que se
muestra. Ningún error lleva el detalle técnico (eso queda en el log).
"""
import functools
import os
import subprocess

from miauki import app_info, paths
from miauki.core import (actualizador, analyzer, clipboard, cookies, diagnostico,
                         errors, history, motor, queue_manager, settings, sites,
                         validacion)
from miauki.core.errors import ErrorMiauki
from miauki.core.logger import obtener_logger


def _error(codigo: str, mensaje: str) -> dict:
    return {"ok": False, "error": {"codigo": codigo, "mensaje": mensaje}}


def seguro(fn):
    """Envuelve un método del puente: nunca deja escapar excepciones."""

    @functools.wraps(fn)
    def _envuelto(self, *args, **kwargs):
        try:
            return {"ok": True, "data": fn(self, *args, **kwargs)}
        except ErrorMiauki as exc:
            obtener_logger().info("Puente api.%s: error %s", fn.__name__, exc.codigo)
            return _error(exc.codigo, exc.mensaje)
        except settings.AjusteInvalido as exc:
            # Validación en el borde: el mensaje ya es amable y en español.
            return _error("ajuste_invalido", str(exc))
        except Exception:
            obtener_logger().exception("Error en el puente api.%s", fn.__name__)
            return _error("error_desconocido", errors.MENSAJES["error_desconocido"])

    return _envuelto


class Api:
    """Clase expuesta a la interfaz como pywebview.api."""

    def __init__(self, cola=None, abre=None, dialogo_carpeta=None,
                 ruta_ajustes=None, abre_archivo=None, abre_url=None,
                 copia=None, historial=None, dialogo_archivo=None):
        # DI para tests: cola (B4), abre (abrir carpeta), dialogo_carpeta
        # (selector de carpetas), ruta_ajustes (archivo de ajustes), abre_url
        # (navegador), copia (portapapeles), historial (Fase 6) y
        # dialogo_archivo (selector de archivos de cookies, Fase 9 B2b).
        self._cola = cola
        self._abre = abre
        self._abre_archivo = abre_archivo
        self._abre_url = abre_url
        self._copia = copia
        self._historial = historial
        self._dialogo_carpeta = dialogo_carpeta
        self._dialogo_archivo = dialogo_archivo
        self._ruta_ajustes = ruta_ajustes

    def _la_cola(self):
        return self._cola if self._cola is not None else queue_manager.obtener()

    def _el_historial(self):
        return self._historial if self._historial is not None else history.obtener()

    @seguro
    def ping(self) -> str:
        return "pong"

    @seguro
    def info(self, idioma: str = "es") -> dict:
        """Datos de Acerca de; con idioma "en" devuelve los textos en inglés."""
        en = str(idioma).lower().startswith("en")
        return {
            "nombre": app_info.NOMBRE,
            "version": app_info.VERSION,
            "autor": app_info.AUTOR,
            "descripcion": app_info.DESCRIPCION_EN if en else app_info.DESCRIPCION,
            "lema": app_info.LEMA,
            "anio": app_info.ANIO,
            "enlaces": dict(app_info.ENLACES),
            "texto_legal": app_info.TEXTO_LEGAL_EN if en else app_info.TEXTO_LEGAL,
            "texto_gracias": (app_info.TEXTO_GRACIAS_EN if en
                              else app_info.TEXTO_GRACIAS),
            "licencia": app_info.LICENCIA_EN if en else app_info.LICENCIA,
            "donacion": {
                "texto": app_info.TEXTO_APOYO_EN if en else app_info.TEXTO_APOYO,
                "alias": app_info.ALIAS_DONACION,
                "usdt": app_info.USDT_DONACION,
                "usdt_red": app_info.USDT_DONACION_RED,
            },
        }

    @seguro
    def obtener_ajustes(self) -> dict:
        """Ajustes actuales (única fuente: settings)."""
        return settings.cargar()

    @seguro
    def cambiar_ajuste(self, clave: str, valor) -> dict:
        """Cambia un ajuste validado y lo devuelve con el resto."""
        return settings.cambiar(clave, valor)

    @seguro
    def analizar(self, url) -> dict:
        """Analiza un link (§7): un análisis a la vez (A3), con id de solicitud.

        Validación en el borde: solo strings; el resto lo resuelve el core.
        """
        if not isinstance(url, str) or not url.strip():
            raise ErrorMiauki("link_invalido")
        return analyzer.analizar(url)

    # ---------- portapapeles (Fase 5 Parte B, B1) ----------

    @seguro
    def link_portapapeles(self) -> dict:
        """Link del portapapeles para la barra de aviso.

        Solo devuelve el link, nunca el texto completo, y no se registra nada
        de lo leído: la privacidad es parte del contrato.
        """
        return {"url": clipboard.link_del_portapapeles()}

    @seguro
    def pegar_link(self) -> dict:
        """Ctrl+V (Fase 7, B2): lee el portapapeles UNA vez y valida el link.

        Lo leído no se registra. El sitio lo decide `sites` acá, en el borde,
        no la interfaz. Devuelve el link canónico o `None`.
        """
        return self._validar_texto(clipboard.texto_del_portapapeles() or "")

    @seguro
    def validar_texto(self, texto) -> dict:
        """¿Este texto (pegado o arrastrado) trae un link que sabemos bajar?"""
        return self._validar_texto(texto)

    def _validar_texto(self, texto) -> dict:
        """Saca el link de un texto y lo valida con `sites`.

        `texto` puede venir del portapapeles o de arrastrar y soltar. Se
        aceptan links sueltos o dentro de una frase; lo que no sea un link
        de un sitio soportado devuelve `None` con el motivo.
        """
        if not isinstance(texto, str):
            return {"url": None, "motivo": "no_link"}
        url = clipboard.link_en_texto(texto)
        if not url:
            return {"url": None, "motivo": "no_link"}
        try:
            _sitio, canonica = sites.detectar(url)
        except ErrorMiauki:
            return {"url": None, "motivo": "sin_sitio"}
        return {"url": canonica, "motivo": ""}

    # ---------- cola de descargas (Fase 4 B4, decisiones 3d.12) ----------

    @seguro
    def agregar_descarga(self, snapshot) -> dict:
        """Encola el snapshot completo del análisis y devuelve su id.

        El snapshot se limpia y valida en el borde (validacion.snapshot_limpio):
        solo claves permitidas, tipos y largos acotados. La interfaz no puede
        meter rutas de salida ni opciones de yt-dlp (el descargador arma sus
        opciones solo con claves conocidas).
        """
        ident = self._la_cola().agregar(validacion.snapshot_limpio(snapshot))
        return {"id": ident}

    @seguro
    def agregar_playlist(self, snapshot) -> dict:
        """Encola una playlist completa (plan de playlists, Paso 5).

        El snapshot trae 'entradas' (lista de snapshots de video, cada uno
        ya elegido en la pantalla de playlist). Todo pasa por el mismo borde
        (validacion.snapshot_limpio): hasta 100 entradas, cada una con sus
        tipos y largos acotados.
        """
        ids = self._la_cola().agregar_playlist(validacion.snapshot_limpio(snapshot))
        return {"ids": ids, "cantidad": len(ids),
                "bloques": (len(ids) + validacion.TAM_BLOQUE - 1)
                // validacion.TAM_BLOQUE}

    def _accion_cola(self, metodo: str, ident):
        if not isinstance(ident, str) or not ident:
            return False
        return bool(getattr(self._la_cola(), metodo)(ident))

    @seguro
    def pausar_descarga(self, ident) -> bool:
        return self._accion_cola("pausar", ident)

    @seguro
    def reanudar_descarga(self, ident) -> bool:
        return self._accion_cola("reanudar", ident)

    @seguro
    def cancelar_descarga(self, ident) -> bool:
        return self._accion_cola("cancelar", ident)

    @seguro
    def reintentar_descarga(self, ident) -> bool:
        return self._accion_cola("reintentar", ident)

    @seguro
    def borrar_descarga(self, ident) -> bool:
        return self._accion_cola("borrar", ident)

    @seguro
    def limpiar_descargas(self) -> int:
        """Quita de la lista las descargas terminadas y canceladas (F5)."""
        return self._la_cola().limpiar()

    @seguro
    def pausar_todo(self) -> int:
        """Pausa todas las descargas activas (plan archivos y cola)."""
        return self._la_cola().pausar_todo()

    @seguro
    def reanudar_todo(self) -> int:
        """Reanuda todas las descargas pausadas."""
        return self._la_cola().reanudar_todo()

    @seguro
    def cancelar_todo(self) -> int:
        """Cancela todas las descargas activas (espera/descargando/procesando/
        pausa). Quedan como "cancelada" en la cola hasta que el usuario las
        borre con el tacho (ajustes 21/11: el método faltaba en el puente y
        el botón global no hacía nada)."""
        return self._la_cola().cancelar_todo()

    @seguro
    def limpiar_historial_cola(self) -> int:
        """Tacho: borra TODO el historial de la Cola (los archivos quedan)."""
        return self._la_cola().limpiar_historial()

    @seguro
    def cola_actual(self) -> list:
        """La lista de ítems para que la interfaz pinte (evento cola)."""
        return self._la_cola().items()

    # ---------- historial (Fase 6, B1) ----------

    @seguro
    def listar_historial(self) -> list:
        """Entradas de la más nueva a la más vieja, con `existe` calculado."""
        entradas = self._el_historial().listar()
        for entrada in entradas:
            ruta = entrada.get("ruta") or ""
            entrada["existe"] = bool(ruta) and os.path.isfile(ruta)
        return entradas

    @seguro
    def quitar_del_historial(self, ident) -> bool:
        """Quita UNA entrada del historial. NO borra el archivo descargado."""
        return self._el_historial().quitar(ident)

    @seguro
    def borrar_historial(self) -> int:
        return self._el_historial().borrar()

    def _entrada_historial(self, ident) -> dict:
        """Entrada por ID (nunca por ruta): la ruta la pone el historial."""
        entrada = self._el_historial().obtener(ident)
        if entrada is None:
            raise ErrorMiauki("historial_no_encontrado")
        return entrada

    @seguro
    def volver_a_bajar(self, ident) -> dict:
        """Encola de nuevo una entrada del historial, por ID."""
        entrada = self._entrada_historial(ident)
        tipo = entrada.get("tipo")
        snapshot = {
            "url_canonica": entrada.get("url_canonica"),
            "tipo": tipo,
            "selector": entrada.get("selector") or ("best" if tipo != "imagen" else None),
            "contenedor": entrada.get("contenedor") if tipo != "musica" else None,
            "kbps": entrada.get("kbps") if tipo == "musica" else None,
            "titulo": entrada.get("titulo"),
            "miniatura": entrada.get("miniatura") or "",
            "con_subs": entrada.get("con_subs") is True,
            "resolucion": entrada.get("resolucion"),
            "sitio": entrada.get("sitio"),
        }
        if snapshot["contenedor"] not in (None, "mp4", "mkv"):
            snapshot["contenedor"] = None
        return {"id": self._la_cola().agregar(validacion.snapshot_limpio(snapshot))}

    @seguro
    def abrir_carpeta_historial(self, ident) -> bool:
        """Abre la carpeta de una entrada del historial (ruta tomada del archivo)."""
        entrada = self._entrada_historial(ident)
        carpeta = os.path.dirname(entrada.get("ruta") or "")
        if not carpeta or not os.path.isdir(carpeta):
            raise ErrorMiauki("archivo_no_encontrado")
        (self._abre or os.startfile)(carpeta)
        return True

    @seguro
    def mostrar_archivo_historial(self, ident) -> bool:
        entrada = self._entrada_historial(ident)
        ruta = entrada.get("ruta") or ""
        if not ruta or not os.path.isfile(ruta):
            raise ErrorMiauki("archivo_no_encontrado")
        (self._abre_archivo or _revelar_en_explorador)(ruta)
        return True

    # ---------- Acerca de... (Fase 5C, A4) ----------

    @seguro
    def abrir_registros(self) -> bool:
        """Abre SOLO la carpeta de registros de Miauki."""
        (self._abre or os.startfile)(str(paths.dir_logs()))
        return True

    @seguro
    def copiar_diagnostico(self) -> dict:
        """Copia versiones (sin rutas, links, cookies ni títulos)."""
        texto = diagnostico.texto()
        copiado = (self._copia or clipboard.copiar_texto)(texto)
        return {"texto": texto, "copiado": bool(copiado)}

    @seguro
    def copiar_alias(self) -> dict:
        """Copia el alias de donación. El texto sale de app_info, no del JS."""
        copiado = (self._copia or clipboard.copiar_texto)(app_info.ALIAS_DONACION)
        return {"alias": app_info.ALIAS_DONACION, "copiado": bool(copiado)}

    @seguro
    def copiar_usdt(self) -> dict:
        """Copia la dirección USDT (TRC20) de donación (20/11/2026)."""
        copiado = (self._copia or clipboard.copiar_texto)(app_info.USDT_DONACION)
        return {"direccion": app_info.USDT_DONACION, "copiado": bool(copiado)}

    @seguro
    def detalles_tecnicos(self, idioma: str = "es") -> list:
        """Las mismas líneas del diagnóstico, sin tocar el portapapeles.

        El idioma llega de la interfaz (es/en) para las etiquetas.
        """
        return diagnostico.lineas(idioma)

    # ---------- motor de descargas (Fase 7, Parte A) ----------

    @seguro
    def estado_motor(self) -> dict:
        """Versión en uso, de dónde salió y cuándo se comprobó (para Ajustes)."""
        datos = motor.estado()
        return {
            "version": motor.version_en_uso(),
            "origen": motor.origen_en_uso(),
            "incluida": app_info.MOTOR_INCLUIDO,
            "ultima": datos.get("ultima_comprobacion"),
            "auto": settings.cargar(self._ruta_ajustes).get(
                "actualizar_motor_auto") is not False,
        }

    @seguro
    def comprobar_motor(self) -> dict:
        """Botón "Buscar actualización": comprueba, prueba y activa."""
        ya_importado = motor.esta_importado()
        resultado = actualizador.comprobar(forzar=True)
        return {
            "accion": resultado.get("accion"),
            "version": motor.version_en_uso(),
            "origen": motor.origen_en_uso(),
            "en_uso_ya": not ya_importado and resultado.get("accion") == "actualizada",
        }

    @seguro
    def comprobar_actualizacion_app(self) -> dict:
        """Botón "Buscar actualizaciones" de la app (plan 19/11).

        Todavía no hay una fuente definida: Maki indicó dejarlo listo y
        conectarlo cuando defina dónde publicar las versiones (ver
        app_info.URL_ACTUALIZACIONES_APP).
        """
        # TODO(actualizaciones): cuando exista la fuente, implementar la
        # comprobación real contra app_info.URL_ACTUALIZACIONES_APP y
        # devolver {configurado: True, hay_novedad, version, url}.
        return {"configurado": bool(app_info.URL_ACTUALIZACIONES_APP)}

    @seguro
    def abrir_enlace(self, clave) -> bool:
        """Abre un enlace de la LISTA BLANCA (la interfaz manda una clave).

        Nunca se acepta una URL desde JavaScript: si la clave no está en
        app_info.ENLACES (o no es "licencias"), no se abre nada.
        """
        if clave == "licencias":
            return self._abrir_licencias()
        url = app_info.ENLACES.get(clave) if isinstance(clave, str) else None
        if not url:
            raise ErrorMiauki("link_invalido")
        (self._abre_url or os.startfile)(url)
        return True

    def _abrir_licencias(self) -> bool:
        """Abre LICENCIAS.txt: primero junto al .exe, después el embebido."""
        for candidata in (paths.dir_del_programa() / "LICENCIAS.txt",
                          paths.recursos() / "LICENCIAS.txt",
                          paths.recursos() / "miauki" / "LICENCIAS.txt"):
            if candidata.is_file():
                (self._abre_archivo or os.startfile)(str(candidata))
                return True
        raise ErrorMiauki("licencias_faltan")

    # ---------- carpetas (Fase 4 B5, endurecido en P0.7) ----------

    def _carpeta_ajustes(self) -> str:
        return settings.cargar(self._ruta_ajustes).get("carpeta_descargas") or ""

    def _ruta_abrible(self, destino: str) -> bool:
        """Solo se puede abrir la carpeta de ajustes (o algo dentro) o la
        carpeta/archivo de un ítem de la cola. Nada más."""
        base = self._carpeta_ajustes()
        if base and validacion.dentro_de(destino, base):
            return True
        destino_n = os.path.normcase(os.path.abspath(destino))
        for item in self._la_cola().items():
            r = item.get("ruta")
            if not isinstance(r, str) or not r:
                continue
            if destino_n in (os.path.normcase(os.path.abspath(r)),
                             os.path.normcase(os.path.abspath(os.path.dirname(r)))):
                return True
        return False

    @seguro
    def abrir_carpeta(self, ruta=None) -> bool:
        """Abre una carpeta en el explorador de Windows.

        Sin ruta usa la carpeta de descargas de los ajustes. Si se pasa una
        ruta, tiene que estar dentro de la carpeta de ajustes o ser la carpeta
        de un archivo de la cola (si no, devuelve False sin abrir nada).
        """
        base = self._carpeta_ajustes()
        if ruta is None or (isinstance(ruta, str) and not ruta.strip()):
            destino = base
        elif isinstance(ruta, str):
            destino = os.path.dirname(ruta) if os.path.isfile(ruta) else ruta
        else:
            raise ErrorMiauki("link_invalido")
        if not isinstance(destino, str) or not destino.strip():
            raise ErrorMiauki("link_invalido")
        if not self._ruta_abrible(destino) or not os.path.isdir(destino):
            return False
        (self._abre or os.startfile)(destino)
        return True

    @seguro
    def mostrar_archivo(self, ruta) -> bool:
        """Revela un archivo de un ítem de la cola en el explorador.

        Solo archivos de la cola (o dentro de la carpeta de ajustes): evita
        que la interfaz mande abrir una ruta arbitraria.
        """
        if not isinstance(ruta, str) or not ruta.strip():
            raise ErrorMiauki("link_invalido")
        if not os.path.isfile(ruta) or not self._ruta_abrible(os.path.dirname(ruta)):
            return False
        lanzar = self._abre_archivo or _revelar_en_explorador
        lanzar(ruta)
        return True

    def _elegir_carpeta(self):
        """Selector de carpetas de pywebview (o el falso de los tests)."""
        if self._dialogo_carpeta is not None:
            return self._dialogo_carpeta()
        import webview
        ventanas = getattr(webview, "windows", None) or []
        if not ventanas:
            return ()
        return ventanas[0].create_file_dialog(webview.FOLDER_DIALOG,
                                              allow_multiple=False)

    @seguro
    def cambiar_carpeta(self):
        """Abre el selector y valida la carpeta elegida antes de guardarla.

        Rechaza rutas peligrosas (raíz de una unidad, Windows, Archivos de
        programa) y carpetas donde no se pueda escribir. Devuelve la nueva
        ruta, o None si el usuario canceló o la carpeta no sirve.
        """
        elegidas = self._elegir_carpeta()
        if not elegidas:
            return None
        ruta = elegidas[0] if isinstance(elegidas, (list, tuple)) \
            else str(elegidas)
        ruta = str(ruta)
        if not ruta.strip() or not os.path.isdir(ruta):
            return None
        if validacion.carpeta_peligrosa(ruta) or not validacion.puede_escribir(ruta):
            obtener_logger().info("Carpeta de descargas rechazada: %s", ruta)
            return None
        settings.cambiar("carpeta_descargas", ruta, ruta=self._ruta_ajustes)
        return ruta

    # ---------- archivo de cookies (Fase 9, B2b) ----------

    def _elegir_archivo(self):
        """Selector de archivos de pywebview (o el falso de los tests)."""
        if self._dialogo_archivo is not None:
            return self._dialogo_archivo()
        import webview
        ventanas = getattr(webview, "windows", None) or []
        if not ventanas:
            return ()
        return ventanas[0].create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False,
            file_types=("Archivos de cookies (*.txt;*.json;*.cookies)",
                        "Todos los archivos (*.*)"))

    @seguro
    def elegir_archivo_cookies(self) -> dict:
        """Elige un cookies.txt Netscape y guarda **solo la ruta**.

        El archivo no se copia ni se lee más allá de la validación de formato:
        el contenido (que da acceso a la cuenta) nunca se guarda ni se registra.
        """
        elegidos = self._elegir_archivo()
        if not elegidos:
            return {"archivo": settings.cargar(self._ruta_ajustes).get("archivo_cookies") or ""}
        ruta = elegidos[0] if isinstance(elegidos, (list, tuple)) else str(elegidos)
        ruta = cookies.archivo_valido(str(ruta))
        obtener_logger().info("Archivo de cookies elegido: %s", os.path.basename(ruta))
        settings.cambiar("archivo_cookies", ruta, ruta=self._ruta_ajustes)
        return {"archivo": ruta}

    @seguro
    def quitar_archivo_cookies(self) -> dict:
        """Vuelve a usar solo el navegador elegido (o ninguno)."""
        settings.cambiar("archivo_cookies", "", ruta=self._ruta_ajustes)
        return {"archivo": ""}


def _revelar_en_explorador(ruta: str) -> None:
    """Abre el explorador con el archivo seleccionado (sin shell)."""
    subprocess.run(["explorer", "/select,", os.path.normpath(ruta)],
                   check=False)

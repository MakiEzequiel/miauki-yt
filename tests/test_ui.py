# -*- coding: utf-8 -*-
"""Reglas de producto de la barra lateral (Fase 2B): 5 ítems y un solo seleccionado."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HTML = RAIZ / "miauki" / "ui" / "index.html"

ORDEN_ESPERADO = ["Inicio", "Cola de Descargas", "Historial", "Ajustes", "Acerca de..."]


class NavegacionLateral(unittest.TestCase):
    def _html(self) -> str:
        return HTML.read_text(encoding="utf-8")

    def test_cinco_items_en_el_orden_de_la_especificacion(self):
        items = re.findall(r'class="nav-item"[^>]*title="([^"]+)"', self._html())
        self.assertEqual(items, ORDEN_ESPERADO)

    def test_solo_un_item_marcado_como_actual(self):
        self.assertEqual(self._html().count('aria-current="page"'), 1)

    def test_el_actual_es_inicio(self):
        html = self._html()
        self.assertIn('title="Inicio" aria-current="page"', html)

    def test_punto_entrada_del_contador_de_cola(self):
        js = (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("actualizarCola", js)
        self.assertIn("app.js", self._html())


class AssetsEnElManifiesto(unittest.TestCase):
    """Todo asset que la interfaz referencia debe estar en la lista blanca
    (evita el bug del .exe que no cargaba el banner por manifiesto viejo)."""

    def test_todo_asset_referenciado_esta_en_el_manifiesto(self):
        manifiesto = {
            linea.strip()
            for linea in (RAIZ / "tools" / "assets_manifest.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if linea.strip() and not linea.startswith("#")
        }
        referenciados = set()

        html = HTML.read_text(encoding="utf-8")
        for atributo in ("src", "href"):
            for valor in re.findall(rf'{atributo}="([^"]+)"', html):
                if "assets/" in valor:
                    ruta = valor.split("#")[0]  # <use href="...svg#ico-x">
                    referenciados.add("miauki/ui/" + ruta.lstrip("./"))

        for css in (RAIZ / "miauki" / "ui" / "css").glob("*.css"):
            for valor in re.findall(r'url\(["\']?([^"\')]+)', css.read_text(encoding="utf-8")):
                if "assets/" in valor:
                    ruta = valor.replace("../", "").lstrip("./")
                    referenciados.add("miauki/ui/" + ruta)

        for js in (RAIZ / "miauki" / "ui" / "js").glob("*.js"):
            for valor in re.findall(r'["\']((?:\.\./)?assets/[^"\']+)["\']',
                                    js.read_text(encoding="utf-8")):
                ruta = valor.split("#")[0].replace("../", "").lstrip("./")
                if "." not in ruta.rsplit("/", 1)[-1]:
                    continue  # armado dinámico ("assets/icons/" + nombre): no es un archivo
                referenciados.add("miauki/ui/" + ruta)

        self.assertTrue(referenciados, "no se encontró ningún asset referenciado")
        faltantes = sorted(referenciados - manifiesto)
        self.assertEqual(faltantes, [], f"Assets referenciados sin estar en el manifiesto: {faltantes}")

    def test_los_iconos_del_manifiesto_existen_en_disco(self):
        faltantes = []
        for linea in (RAIZ / "tools" / "assets_manifest.txt").read_text(encoding="utf-8").splitlines():
            ruta = linea.strip()
            if ruta.endswith(".svg") and not (RAIZ / ruta).is_file():
                faltantes.append(ruta)
        self.assertEqual(faltantes, [], f"Íconos del manifiesto inexistentes: {faltantes}")

    def test_los_assets_referenciados_existen_en_disco(self):
        html = HTML.read_text(encoding="utf-8")
        faltantes = []
        for valor in re.findall(r'src="(assets/[^"]+)"', html):
            if not (RAIZ / "miauki" / "ui" / valor.split("#")[0]).is_file():
                faltantes.append(valor)
        self.assertEqual(faltantes, [], f"Archivos referenciados inexistentes: {faltantes}")


class TextosEnStrings(unittest.TestCase):
    """Todo marcador de texto del HTML (data-str/-ph/-aria) tiene su clave
    en strings.es.js: la fuente única de verdad no puede quedar desincronizada."""

    def test_toda_clave_del_html_existe_en_strings(self):
        html = HTML.read_text(encoding="utf-8")
        claves = set(re.findall(r'data-str(?:-ph|-aria)?="([^"]+)"', html))
        js = (RAIZ / "miauki" / "ui" / "js" / "strings.es.js").read_text(encoding="utf-8")
        faltantes = sorted(k for k in claves if '"{}"'.format(k) not in js)
        self.assertTrue(claves, "el HTML no tiene ningún data-str (¿se perdió?)")
        self.assertEqual(faltantes, [], f"Claves sin texto en strings.es.js: {faltantes}")

    def test_strings_es_cargado_antes_de_app(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn('src="js/strings.es.js"', html)
        self.assertLess(html.index("strings.es.js"), html.index("js/app.js"))


class BarraPortapapeles(unittest.TestCase):
    """Fase 2D: la barra nace oculta e inerte (el .exe nunca la muestra;
    solo la demo ?portapapeles=1 la activa)."""

    def _html(self) -> str:
        return HTML.read_text(encoding="utf-8")

    def test_app_nace_con_sin_inferior(self):
        self.assertIn('class="app sin-inferior"', self._html())

    def test_barra_nace_inerte(self):
        self.assertRegex(self._html(),
                         r'<footer class="vidrio barra-inferior"[^>]*\binert\b')

    def test_la_region_viva_es_el_aviso_y_no_la_barra(self):
        """Una región viva no puede envolver el input ni los botones."""
        html = self._html()
        self.assertNotRegex(html, r'<footer class="vidrio barra-inferior"[^>]*role=')
        self.assertIn('<p class="barra-aviso" role="status" aria-live="polite">', html)

    def test_gancho_y_demo_en_app_js(self):
        js = (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("mostrarBarraPortapapeles", js)
        self.assertIn("portapapeles=1", js)
        self.assertIn("ocultarBarraPortapapeles", js)


class FlujoAnalisis3B(unittest.TestCase):
    """Fase 3B: la interfaz llama al motor real con reglas de seguridad fijas."""

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _html(self) -> str:
        return HTML.read_text(encoding="utf-8")

    def test_app_js_nunca_usa_innerhtml(self):
        js = self._js()
        for patron in ("innerHTML", "outerHTML", "insertAdjacentHTML"):
            self.assertNotIn(patron, js,
                             f"app.js usa {patron}: los datos del análisis "
                             "deben entrar solo por textContent (§7)")

    def test_csp_permite_miniaturas_data_uri(self):
        # Las miniaturas del análisis son data:image/... (CSP no abre la red).
        self.assertIn("img-src 'self' data:", self._html())
        self.assertNotIn("img-src 'self' data: https:", self._html())

    def test_el_error_del_analizacion_es_role_alert(self):
        html = self._html()
        self.assertIn('id="paso1-error"', html)
        self.assertIn('class="paso1-error" id="paso1-error" role="alert"', html)

    def test_miniatura_y_fotos_solo_data_image(self):
        js = self._js()
        # Cada src que viene del análisis está tras un chequeo data:image/.
        self.assertIn('String(data.miniatura).indexOf("data:image/") === 0', js)
        self.assertIn('uri.indexOf("data:image/") !== 0', js)
        self.assertNotIn("src = data.imagenes", js)

    def test_llamada_al_motor_pasa_por_when_ready(self):
        js = self._js()
        self.assertIn("window.pywebview.api.analizar(url)", js)
        # el análisis real vive dentro de whenReady (no asume api lista)
        bloque = js[js.index("function analizar()"):
                    js.index("function iniciarMasOpciones")]
        self.assertIn("whenReady", bloque)
        self.assertIn("estadoBotones(true, false)", bloque)  # busy + sin doble envío
        self.assertIn("aria-busy", js)

    def test_validacion_local_no_llama_al_motor(self):
        js = self._js()
        inicio = js.index("function analizar()")
        guard = js.index("whenReady", inicio)
        previo = js[inicio:guard]
        self.assertIn('str("errores.vacio")', previo)
        self.assertIn('str("errores.formato")', previo)
        # Plan `plan.md`, paso 3.3: la validación local usa normalizarUrl
        # (http(s), www. y dominio con ruta) en vez de exigir http(s).
        self.assertIn("normalizarUrl(url)", previo)
        self.assertIn("function normalizarUrl", js)

    def test_respuestas_viejas_se_descartan(self):
        js = self._js()
        self.assertIn("nLanzamiento", js)
        self.assertIn("if (n !== nLanzamiento) return;", js)

    def test_miauk_encola_el_snapshot(self):
        # Fase 4B: el clic de MIAUK! arma el snapshot y llama agregar_descarga.
        js = self._js()
        self.assertIn("miauk.disabled = !listo", js)
        self.assertIn('miauk.addEventListener("click", encolar)', js)
        self.assertIn("agregar_descarga(snapshot)", js)
        # Para imagen manda la URL real (imagenes_urls), nunca data: (3d.13).
        self.assertIn("resultado.imagenes_urls", js)

    def test_subs_escriben_ajuste_real(self):
        js = self._js()
        self.assertIn('cambiar_ajuste("incluir_subs"', js)
        self.assertIn("obtener_ajustes", js)

    def test_ruta_real_de_los_ajustes_en_la_columna(self):
        js = self._js()
        self.assertIn("mostrarRuta", js)
        self.assertIn("carpeta_descargas", js)

    def test_estado_inicial_sin_datos_de_mentira(self):
        # 3B: con el motor conectado, la maqueta no puede nacer con link demo
        # ni textos hardcodeados (el .exe mostraba "Me at the zoo" al abrir).
        html = self._html()
        js = self._js()
        self.assertIn('data-estado-video="vacio"', html)
        self.assertNotIn("BaW_jenozKc", html + js)
        self.assertNotIn("Me at the zoo", html + js)
        self.assertNotIn('str("paso1.demoLink")', js)
        self.assertNotIn("paso2.demoTitulo", html)
        self.assertIn('<p class="video-titulo"></p>', html)


class ColumnaDerecha(unittest.TestCase):
    """Plan de ajustes UI, pasos 1-3: botones de carpeta en Inicio y
    sincronización Ajustes <-> Inicio vía mostrarRuta."""

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _html(self) -> str:
        return (RAIZ / "miauki" / "ui" / "index.html").read_text(encoding="utf-8")

    def test_botones_de_carpeta_existen_en_inicio(self):
        html = self._html()
        self.assertIn("data-cambiar-carpeta", html)
        self.assertIn("data-abrir-carpeta", html)

    def test_cambiar_carpeta_actualiza_todas_las_rutas(self):
        js = self._js()
        # La columna derecha usa el MISMO puente que Ajustes y sincroniza
        # por mostrarRuta (una sola fuente de verdad para la ruta).
        self.assertIn("cambiar_carpeta()", js)
        self.assertIn("iniciarColumnaDerecha", js)

    def test_sincronizacion_ajustes_inicio_por_mostrarruta(self):
        # Regresión (paso 3): tras cambiar la carpeta en Ajustes, el Inicio
        # se actualiza al instante porque el handler llama mostrarRuta.
        js = self._js()
        self.assertIn("mostrarRuta(r.data)", js)

    def test_abrir_carpeta_no_confia_en_la_interfaz(self):
        js = self._js()
        # Sin ruta: Python abre la carpeta de ajustes ya validada.
        self.assertIn("abrir_carpeta()", js)
        self.assertNotIn("abrir_carpeta(ruta)", js)

    def test_refresh_recarga_la_ventana_sin_dialogo(self):
        # Paso 4: dos flechas circulares; recarga al instante, sin confirmar.
        html = self._html()
        js = self._js()
        self.assertIn("data-refresh", html)
        self.assertIn("data-str-aria=\"col.refresh\"", html)
        self.assertIn("ico-reintentar", html)
        self.assertIn('querySelector("[data-refresh]")', js)
        self.assertIn("window.location.reload()", js)

    def test_cerrar_vista_previa_solo_en_sesion(self):
        # Paso 5: el x oculta la tarjeta sin localStorage; limpiarVideo()
        # la reactiva al analizar de nuevo (vuelve a aparecer).
        html = self._html()
        js = self._js()
        self.assertIn("data-cerrar-preview", html)
        self.assertIn("data-str-aria=\"col.cerrarVista\"", html)
        self.assertIn("iniciarCierreVista", js)
        self.assertIn('querySelector(".video-listo")', js)
        self.assertNotIn("localStorage.", js)

    def test_limpiar_el_link_limpia_error_y_vista_previa(self):
        # Auditoría 23/11: después de un análisis fallido, borrar el link
        # dejaba el error y el botón de Ajustes pegados en pantalla.
        js = self._js()
        inicio = js.index("function sincronizar()")
        bloque = js[inicio:js.index('input.addEventListener("input", sincronizar)')]
        self.assertIn("limpiarError()", bloque)
        self.assertIn("limpiarVideo()", bloque)
        self.assertIn('mostrarVideoEstado("vacio")', bloque)

    def test_bloques_en_la_cola_y_en_el_aviso(self):
        # Paso 6.3: la fila muestra "Bloque X/Y" y el aviso dice en cuantos
        # bloques se encolo (el puente devuelve r.data.bloques).
        js = self._js()
        self.assertIn('if (item.bloque) partes.push', js)
        self.assertIn("cola.agregadaBloques", js)
        self.assertIn("mostrarAvisoCola(r.data && r.data.bloques)", js)

    def test_botones_globales_de_la_cola(self):
        # Plan archivos y cola, paso 2: Pausar/Reanudar/Cancelar todo y el
        # tacho a la izquierda del contador; el tacho solo sin activas.
        html = self._html()
        js = self._js()
        self.assertIn("data-cola-pausar-todo", html)
        self.assertIn("data-cola-reanudar-todo", html)
        self.assertIn("data-cola-cancelar-todo", html)
        self.assertIn("data-cola-limpiar-historial", html)
        # El tacho es un icono con nombre accesible, en rojo por CSS.
        self.assertIn('data-str-aria="cola.tacho"', html)
        self.assertIn("ico-borrar", html)
        # Cada boton llama a su metodo del puente.
        for metodo in ("pausar_todo", "reanudar_todo", "cancelar_todo",
                       "limpiar_historial_cola"):
            self.assertIn('"{}"'.format(metodo), js)
        # El tacho exige cero descargas activas.
        self.assertIn("borrables > 0 && activos === 0", js)

    def test_ajuste_tamano_de_fuente(self):
        # Plan 19/11/2026: el predeterminado pasa a ser el que era "Un poco
        # más grande" (html al 110%) y "Un poco más grande" ahora es +10%
        # sobre ese nuevo tamaño (121%).
        html = self._html()
        js = self._js()
        self.assertIn('data-ajuste="tamano_fuente"', html)
        self.assertIn('value="normal"', html)
        self.assertIn('value="grande"', html)
        self.assertIn("aplicarTamanoFuente", js)
        self.assertIn('document.documentElement.classList.toggle("font-grande"',
                      js)
        base = (RAIZ / "miauki" / "ui" / "css" / "base.css").read_text(
            encoding="utf-8")
        self.assertIn("html.font-grande", base)
        self.assertIn("font-size: 110%", base)   # predeterminado nuevo
        self.assertIn("font-size: 121%", base)   # "Un poco más grande" nuevo

    def test_acerca_de_siempre_mas_grande_con_tope(self):
        # Plan archivos y cola, paso 4: la pantalla Acerca de va +10% siempre
        # y, con "Un poco mas grande" activo, topea en 1.17 (nunca 1.20).
        layout = (RAIZ / "miauki" / "ui" / "css" / "layout.css").read_text(
            encoding="utf-8")
        self.assertIn(".pantalla-acerca {\n  zoom: 1.1;", layout)
        self.assertIn("html.font-grande .pantalla-acerca {", layout)
        self.assertIn("zoom: 1.0636;", layout)


class EventosCola(unittest.TestCase):
    """Fase 4B: bridge reparte cola/progreso y la insignia cuenta activos."""

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _bridge(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "bridge.js").read_text(encoding="utf-8")

    def test_el_puente_reparte_por_nombre_de_evento(self):
        puente = self._bridge()
        self.assertIn("window.miaukiEventos", puente)
        self.assertIn("window.MiaukiManejadores", puente)
        self.assertIn("carga.evento", puente)

    def test_app_registra_cola_y_progreso(self):
        js = self._js()
        self.assertIn("window.MiaukiManejadores = {", js)
        self.assertIn("cola: alLlegarCola", js)
        self.assertIn("progreso: alLlegarProgreso", js)
        self.assertIn("actualizarCola(n)", js)

    def test_la_insignia_cuenta_solo_activos(self):
        # Decisión 3d.14: espera/descargando/procesando/pausa; nada de
        # terminadas, error o canceladas.
        js = self._js()
        inicio = js.index("var ESTADOS_ACTIVOS")
        fin = js.index("function alLlegarCola")
        bloque = js[inicio:fin]
        for estado in ("espera", "descargando", "procesando", "pausa"):
            self.assertIn(estado, bloque)


class NavegacionEntrePantallas(unittest.TestCase):
    """Fase 4C Parte B (porción 1): los 5 ítems cambian de pantalla, solo Inicio
    conserva la columna derecha y los placeholders dicen 'llega pronto'."""

    def _html(self) -> str:
        return HTML.read_text(encoding="utf-8")

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _css(self) -> str:
        return (RAIZ / "miauki" / "ui" / "css" / "layout.css").read_text(encoding="utf-8")

    def test_cada_item_declara_su_pantalla_en_orden(self):
        pantallas = re.findall(
            r'class="nav-item" data-pantalla="([^"]+)"[^>]*title=', self._html()
        )
        self.assertEqual(pantallas, ["inicio", "cola", "historial", "ajustes", "acerca"])

    def test_hay_una_pantalla_por_item(self):
        html = self._html()
        for nombre in ("inicio", "cola", "historial", "ajustes", "acerca"):
            self.assertIn('data-pantalla="%s"' % nombre, html)

    def test_los_placeholders_nacen_ocultos_y_avisan(self):
        html = self._html()
        for nombre in ("historial", "ajustes", "acerca"):
            self.assertRegex(html, r'data-pantalla="%s"[^>]*hidden' % nombre)
            self.assertIn('data-str="pantalla.%s"' % nombre, html)
        # F6 B2: Historial ya es real (lista + estado vacío + borrar con confirmación).
        for marca in ("data-hist-lista", "data-hist-vacia", "data-hist-borrar",
                      "data-hist-confirmar"):
            self.assertIn(marca, html)

    def test_h1_por_pantalla_y_enfocable(self):
        html = self._html()
        for ident in ("t-pantalla-inicio", "t-pantalla-cola", "t-pantalla-historial",
                      "t-pantalla-ajustes", "t-pantalla-acerca"):
            self.assertRegex(html, r'id="%s"[^>]*tabindex="-1"' % ident)

    def test_app_js_cambia_de_pantalla_y_cierra_la_columna(self):
        js = self._js()
        self.assertIn("function mostrarPantalla(", js)
        self.assertIn("PANTALLAS", js)
        self.assertIn('classList.toggle("sin-derecha"', js)
        self.assertIn("el.hidden = el.getAttribute", js)

    def test_css_oculta_pantallas_inactivas_y_cierra_grilla(self):
        css = self._css()
        self.assertIn(".central [data-pantalla][hidden]", css)
        self.assertIn(".app.sin-derecha", css)


class PantallaColaEstructura(unittest.TestCase):
    """Fase 4C Parte B (porción 2): esqueleto de la Cola + estado vacío."""

    def _html(self) -> str:
        return HTML.read_text(encoding="utf-8")

    def _css(self) -> str:
        return (RAIZ / "miauki" / "ui" / "css" / "layout.css").read_text(encoding="utf-8")

    def test_lista_semantica_con_gancho(self):
        self.assertIn('<ul class="cola-lista" data-cola-lista>', self._html())

    def test_estado_vacio_con_texto_de_strings(self):
        html = self._html()
        self.assertIn('data-cola-vacia', html)
        self.assertIn('data-str="cola.vacia"', html)

    def test_conteo_anunciado_por_lector(self):
        self.assertIn('data-cola-conteo aria-live="polite"', self._html())

    def test_limpiar_nace_oculto(self):
        html = self._html()
        self.assertIn('data-cola-limpiar', html)
        self.assertIn('data-str="cola.limpiar"', html)
        self.assertRegex(html, r'class="cola-limpiar col-boton"[^>]*hidden')

    def test_css_centra_el_vacio_y_oculta_la_lista_sin_items(self):
        css = self._css()
        self.assertIn(".pantalla-cola", css)
        self.assertIn(".cola-lista:empty", css)


class ColaRenderizaEstados(unittest.TestCase):
    """Fase 4C Parte B (porción 3): la lista se dibuja desde el evento 'cola'
    con createElement/textContent y una etiqueta por estado."""

    ESTADOS = ("espera", "descargando", "procesando", "pausa",
               "terminada", "cancelada", "error")

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _strings(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "strings.es.js").read_text(encoding="utf-8")

    def test_dibuja_con_createelement_no_con_texto_crudo(self):
        js = self._js()
        self.assertIn("function pintarCola(", js)
        self.assertIn("function filaDeItem(", js)
        self.assertIn('document.createElement("li")', js)
        self.assertIn('setAttribute("data-cola-id"', js)
        self.assertIn('setAttribute("data-estado"', js)

    def test_cada_estado_tiene_etiqueta_en_strings(self):
        strings = self._strings()
        for estado in self.ESTADOS:
            self.assertIn('"cola.estado.%s"' % estado, strings)
        self.assertIn('str("cola.estado." + estado)', self._js())

    def test_miniatura_solo_acepta_data_image(self):
        js = self._js()
        self.assertIn('uri.indexOf("data:image/") === 0', js)

    def test_el_evento_cola_repinta_la_lista(self):
        js = self._js()
        bloque = js[js.index("function alLlegarCola"):js.index("function cargarColaInicial")]
        self.assertIn("pintarCola(items)", bloque)

    def test_estado_inicial_desde_la_cola_real(self):
        self.assertIn("cola_actual()", self._js())

    def test_conteo_singular_y_plural(self):
        js = self._js()
        self.assertIn("cola.conteo.uno", js)
        self.assertIn("cola.conteo.varios", js)


class ColaAcciones(unittest.TestCase):
    """Fase 4C Parte B (porción 4): acciones por estado de la Cola, con nombre
    accesible en todas (spec: cancelar, reintento; Maki: pausar/reanudar,
    quitar, abrir carpeta y mostrar archivo)."""

    ACCIONES = {
        "espera": ("pausar", "cancelar"),
        "descargando": ("pausar", "cancelar"),
        "procesando": ("cancelar",),
        "pausa": ("reanudar", "cancelar"),
        "error": ("reintentar", "quitar"),
        "terminada": ("carpeta", "archivo", "quitar"),
        "cancelada": ("quitar",),
    }
    ETIQUETAS = ("pausar", "reanudar", "cancelar", "reintentar",
                 "quitar", "abrirCarpeta", "mostrarArchivo")

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _strings(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "strings.es.js").read_text(encoding="utf-8")

    def test_tabla_de_acciones_por_estado(self):
        js = self._js()
        inicio = js.index("var ACCIONES")
        bloque = js[inicio:js.index("var ACCION_INFO")]
        for estado, acciones in self.ACCIONES.items():
            self.assertRegex(bloque, r"%s:\s*\[" % estado)
            for accion in acciones:
                self.assertIn('"%s"' % accion, bloque)

    def test_etiquetas_accesibles_en_strings(self):
        strings = self._strings()
        for clave in self.ETIQUETAS:
            self.assertIn('"cola.accion.%s"' % clave, strings)

    def test_botones_de_icono_tienen_aria_label(self):
        js = self._js()
        self.assertIn('boton.setAttribute("aria-label", str(info.texto))', js)
        self.assertIn("boton.title = str(info.texto)", js)

    def test_cancelar_avanzado_pide_confirmacion_en_linea(self):
        js = self._js()
        self.assertIn("function confirmarCancelar(", js)
        self.assertIn('item.estado === "descargando" || item.estado === "procesando"', js)
        strings = self._strings()
        self.assertIn('"cola.confirmarSi"', strings)
        self.assertIn('"cola.confirmarNo"', strings)

    def test_iconos_de_accion_en_el_manifiesto(self):
        manifiesto = (RAIZ / "tools" / "assets_manifest.txt").read_text(encoding="utf-8")
        for icono in ("pausar", "reanudar", "reintentar", "abrir", "borrar"):
            self.assertIn("icons/%s.svg" % icono, manifiesto)


class ColaProgreso(unittest.TestCase):
    """Fase 4C Parte B (porción 5): barra de progreso por ítem con porcentaje,
    velocidad, tiempo restante y tamaño (sin 'peso total descargado')."""

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _css(self) -> str:
        return (RAIZ / "miauki" / "ui" / "css" / "layout.css").read_text(encoding="utf-8")

    def _strings(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "strings.es.js").read_text(encoding="utf-8")

    def test_barra_solo_en_estados_con_progreso(self):
        js = self._js()
        inicio = js.index("var CON_PROGRESO")
        bloque = js[inicio:js.index("function porcentajeDe")]
        for estado in ("descargando", "procesando", "pausa"):
            self.assertIn(estado, bloque)

    def test_datos_del_progreso_son_los_cuatro_pedidos(self):
        js = self._js()
        inicio = js.index("function textoProgreso")
        bloque = js[inicio:js.index("function barraDeItem")]
        self.assertIn("porcentaje", bloque)   # %
        self.assertIn("velocidad", bloque)    # MB/s
        self.assertIn("restante", bloque)     # tiempo restante
        self.assertIn("total", bloque)        # tamaño
        self.assertIn('"cola.quedan"', self._strings())

    def test_evento_progreso_actualiza_sin_repintar_toda_la_lista(self):
        js = self._js()
        inicio = js.index("function alLlegarProgreso")
        bloque = js[inicio:js.index("window.MiaukiManejadores")]
        self.assertIn("actualizarBarraItem(datos.id, datos)", bloque)
        self.assertNotIn("pintarCola", bloque)

    def test_evento_tardio_no_resucita_item_borrado(self):
        js = self._js()
        # el progreso se descarta si el ítem no está en pantalla
        inicio = js.index("function alLlegarProgreso")
        bloque = js[inicio:js.index("window.MiaukiManejadores")]
        self.assertIn("document.querySelector", bloque)
        self.assertIn("return;", bloque)
        # actualizarBarraItem sale si el ítem no está en el DOM
        self.assertIn("if (!li) return;", js)
        # y la cola poda el progreso de los ids que ya no están
        self.assertIn("delete progresoActual[ident]", js)

    def test_movimiento_suave_y_respetuoso(self):
        css = self._css()
        self.assertIn("transition: width 0.3s linear", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn(".reducir-efectos .cola-barra-fill", css)


class ColaAvisoAgregar(unittest.TestCase):
    """Fase 4C Parte B (porción 6): aviso 'Agregada a la cola' + 'Ver cola'
    debajo del campo del link, con región viva y destello del contador."""

    def _html(self) -> str:
        return (RAIZ / "miauki" / "ui" / "index.html").read_text(encoding="utf-8")

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _css(self) -> str:
        return (RAIZ / "miauki" / "ui" / "css" / "layout.css").read_text(encoding="utf-8")

    def _strings(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "strings.es.js").read_text(encoding="utf-8")

    def test_se_oculta_con_hidden_aunque_sea_flex(self):
        # display:flex le gana al [hidden] del navegador: hace falta la regla propia
        css = self._css()
        self.assertIn(".aviso-cola[hidden]", css)
        self.assertIn(".cola-vacia[hidden]", css)

    def test_aviso_esta_debajo_del_campo_del_link(self):
        html = self._html()
        campo = html.index('class="fila-link"')
        aviso = html.index("data-aviso-cola")
        error = html.index('id="paso1-error"')
        self.assertTrue(campo < aviso < error, "el aviso va debajo del campo del link")

    def test_aviso_tiene_region_viva_y_boton_ver_cola(self):
        html = self._html()
        self.assertIn('role="status"', html)
        self.assertIn("data-aviso-texto", html)
        self.assertIn("data-ver-cola", html)
        self.assertIn('data-str="cola.ver"', html)
        self.assertIn('data-aviso-cola hidden', html)
        self.assertIn('"cola.agregada"', self._strings())
        self.assertIn('"cola.ver"', self._strings())

    def test_aviso_aparece_al_agregar_y_se_oculta_solo(self):
        js = self._js()
        encolar = js[js.index("function encolar"):js.index("function analizar")]
        self.assertIn("mostrarAvisoCola()", encolar)
        aviso = js[js.index("function mostrarAvisoCola"):js.index("function destellarCola")]
        self.assertIn('str("cola.agregada")', aviso)
        self.assertIn("aviso.hidden = false", aviso)
        self.assertIn("setTimeout(ocultarAvisoCola", aviso)

    def test_ver_cola_navega_a_la_pantalla_de_cola(self):
        js = self._js()
        self.assertIn('querySelector("[data-ver-cola]")', js)
        self.assertIn('mostrarPantalla("cola")', js)

    def test_destello_del_contador_respeta_movimiento_reducido(self):
        js = self._js()
        self.assertIn("function destellarCola", js)
        self.assertIn("valor > anterior", js)
        self.assertIn('classList.add("destello")', js)
        css = self._css()
        self.assertIn(".nav-item.destello", css)
        self.assertIn("@keyframes destello-cola", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn(".reducir-efectos .nav-item.destello", css)


class CierreConDescargas(unittest.TestCase):
    """Fase 4C Parte B (porción 7): confirmación al cerrar con descargas en curso."""

    def _app(self) -> str:
        return (RAIZ / "app.py").read_text(encoding="utf-8")

    def test_se_engancha_el_cierre_de_la_ventana(self):
        app = self._app()
        self.assertIn("ventana.events.closing += al_cerrar", app)

    def test_sin_descargas_en_curso_no_pregunta(self):
        app = self._app()
        self.assertIn("n = cola.activos()", app)
        self.assertIn("if n <= 0:", app)
        self.assertIn("return True", app)

    def test_usa_un_dialogo_de_confirmacion_nativo(self):
        self.assertIn("create_confirmation_dialog", self._app())

    def test_mensaje_en_espanol_con_plural(self):
        app = self._app()
        self.assertIn('"descarga" if n == 1 else "descargas"', app)
        self.assertIn("se cancelan", app)


class FormatoNumeros(unittest.TestCase):
    """Fase 5 (Parte 0, punto 5): formato de números de Argentina (coma
    decimal, punto de miles) en UNA sola función usada por toda la interfaz."""

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def test_hay_una_sola_funcion_de_formato(self):
        js = self._js()
        self.assertIn("function formatearNumero(", js)
        self.assertIn(r"\B(?=(\d{3})+(?!\d))", js)   # separador de miles "."
        self.assertIn('"," + partes[1]', js)          # separador decimal ","

    def test_todo_numero_pasa_por_la_funcion(self):
        js = self._js()
        self.assertEqual(
            js.count(".toFixed("), 1,
            "el único toFixed() permitido está dentro de formatearNumero")
        self.assertIn("formatearNumero(v, v >= 10 || i === 0 ? 0 : 1)", js)
        self.assertIn('formatearNumero(p.porcentaje, 0) + " %"', js)

    def test_el_helper_contempla_borde(self):
        js = self._js()
        inicio = js.index("function formatearNumero(")
        bloque = js[inicio:js.index("function formatearBytes")]
        self.assertIn("!isFinite(valor)", bloque)   # null / infinito -> "—"
        self.assertIn('return "—"', bloque)


class PulidoInicio5P0(unittest.TestCase):
    """Fase 5 (Parte 0, punto 8): correcciones visuales de Inicio.
    (a) el h1 de pantalla no dibuja anillo al recibir foco por programa;
    (b) la fila de calidad no envuelve a 1200 (card3 no se corta);
    (c) el aviso de la cola reemplaza a la ayuda y no mueve la tarjeta 1;
    (d) tooltip propio en los botones de solo icono y los de "Guardar en"."""

    def _css(self) -> str:
        return (RAIZ / "miauki" / "ui" / "css" / "layout.css").read_text(encoding="utf-8")

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def _html(self) -> str:
        return (RAIZ / "miauki" / "ui" / "index.html").read_text(encoding="utf-8")

    def test_tarjetas_usan_nth_of_type_y_no_nth_child(self):
        # El h1 sr-only es el 1er hijo de .central: con :nth-child los pisos de
        # las tarjetas se corrían un lugar (card3 sin piso -> scroll a 1200).
        css = self._css()
        self.assertIn(".central .tarjeta:nth-of-type(1)", css)
        self.assertNotIn(".central .tarjeta:nth-child", css)

    def test_h1_de_pantalla_no_dibuja_anillo(self):
        css = self._css()
        self.assertIn(".pantalla-titulo:focus", css)
        self.assertNotIn(".pantalla-titulo:focus-visible", css)

    def test_segmentado_mas_compacto_para_no_envolver(self):
        css = self._css()
        inicio = css.index('.segmentado [role="radio"] {')
        bloque = css[inicio:css.index("}", inicio)]
        self.assertIn("var(--esp-2) var(--esp-3)", bloque)

    def test_aviso_y_ayuda_comparten_altura_reservada(self):
        css = self._css()
        self.assertIn(".ayuda-tenue[hidden]", css)  # display:flex pisa [hidden]
        self.assertIn("min-height: 25px", css)      # misma reserva en los dos
        js = self._js()
        aviso = js[js.index("function mostrarAvisoCola"):js.index("function destellarCola")]
        self.assertIn('querySelector(".ayuda-tenue")', aviso)
        self.assertIn("ayuda.hidden = true", aviso)
        ocultar = js[js.index("function ocultarAvisoCola"):js.index("function mostrarAvisoCola")]
        self.assertIn("ayuda.hidden = false", ocultar)

    def test_tooltip_propio_en_iconos_y_guardar_en(self):
        js = self._js()
        self.assertIn("function iniciarTooltips", js)
        self.assertIn('closest("[data-tooltip]")', js)
        self.assertIn('setAttribute("data-tooltip", str(info.texto))', js)
        self.assertIn("iniciarTooltips()", js)
        css = self._css()
        self.assertIn(".globo {", css)
        self.assertIn(".globo[hidden]", css)
        html = self._html()
        self.assertIn('data-str="col.cambiar" data-tooltip', html)
        self.assertIn('data-str="col.abrirCarpeta" data-tooltip', html)


class FocoCola5P0(unittest.TestCase):
    """Fase 5 (Parte 0, punto 3): el progreso actualiza en el lugar (no repinta)
    y repintar devuelve el foco al botón equivalente en vez de tirarlo al body."""

    def _js(self) -> str:
        return (RAIZ / "miauki" / "ui" / "js" / "app.js").read_text(encoding="utf-8")

    def test_repintar_devuelve_el_foco_al_boton_equivalente(self):
        js = self._js()
        pintar = js[js.index("function pintarCola"):js.index("function alLlegarCola")]
        borra = pintar.index("while (lista.firstChild)")
        recuerda = pintar.index("document.activeElement")
        self.assertLess(recuerda, borra, "el foco se recuerda ANTES de vaciar la lista")
        self.assertIn('foco.classList.contains("cola-btn")', pintar)
        self.assertIn("data-cola-id=", pintar)
        self.assertIn("data-accion=", pintar)
        self.assertIn("if (devuelto) devuelto.focus();", pintar)

    def test_el_progreso_actualiza_sin_repintar(self):
        js = self._js()
        actualizar = js[js.index("function actualizarBarraItem"):js.index("// Acciones por estado")]
        self.assertNotIn("pintarCola", actualizar)
        self.assertIn(".cola-barra-fill", actualizar)


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    unittest.main()

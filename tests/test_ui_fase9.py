# -*- coding: utf-8 -*-
"""Fase 9 B: aviso de "solo imágenes", atajo a Ajustes y barra arrastrable.

La barra flotante se puede mover con el mouse (pointer events) y con las
flechas del teclado, no se sale de la ventana, el conteo de 10 s se pausa
mientras se arrastra y cada barra nueva vuelve a su lugar.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
UI = RAIZ / "miauki" / "ui"
HTML = (UI / "index.html").read_text(encoding="utf-8")
JS = (UI / "js" / "app.js").read_text(encoding="utf-8")
CSS = (UI / "css" / "layout.css").read_text(encoding="utf-8")
TOKENS = (UI / "css" / "tokens.css").read_text(encoding="utf-8")
STRINGS = (UI / "js" / "strings.es.js").read_text(encoding="utf-8")


def tokens() -> dict:
    """Base de tokens.css: manda la PRIMERA definición.

    Los `@media` del final son escalones (ancho compacto, altura media); para
    las pruebas de tamaño base no cuentan.
    """
    salida = {}
    for nombre, valor in re.findall(r"(--[\w-]+):\s*([^;]+);", TOKENS):
        salida.setdefault(nombre, valor)
    return salida


class AvisoSoloImagen(unittest.TestCase):
    """B3: el post de solo fotos apaga Video y Música de verdad y lo explica."""

    def test_el_aviso_existe_y_nace_oculto(self):
        self.assertRegex(
            HTML, r'<p class="tipo-nota"[^>]*data-tipo-nota[^>]*data-str="paso3.soloImagen"')
        self.assertRegex(
            HTML, r'<p class="tipo-nota"[^>]*data-tipo-nota[^>]*data-str="paso3.soloImagen"[^>]*hidden')

    def test_el_aviso_tiene_texto_propio(self):
        self.assertIn('"paso3.soloImagen":', STRINGS)

    def test_se_muestra_solo_si_el_unico_tipo_es_imagen(self):
        self.assertIn('document.querySelector("[data-tipo-nota]")', JS)
        self.assertIn('tipos.length === 1 && tipos[0] === "imagen"', JS)

    def test_video_y_musica_quedan_deshabilitados_de_verdad(self):
        # `disabled` real (no alcanza con aria-disabled) + el atributo ARIA.
        self.assertIn("radio.disabled = !esta;", JS)
        self.assertIn('radio.setAttribute("aria-disabled"', JS)

    def test_el_backend_decide_los_tipos(self):
        from miauki.core.analyzer import analizar  # noqa: F401
        from miauki.core import images

        # El dato sale del motor (tipos), no de una suposición de la interfaz.
        self.assertTrue(hasattr(images, "es_imagen_x_directa") or
                        hasattr(images, "imagenes_de"))

    def test_el_aviso_tiene_estilo_propio(self):
        self.assertRegex(CSS, r"\.tipo-nota\s*\{[^}]*font-size")


class AtajoAAjustes(unittest.TestCase):
    """B2: cuando el contenido pide sesión, hay un botón que lleva a Ajustes."""

    def test_el_boton_existe_y_nace_oculto(self):
        self.assertRegex(HTML, r'data-error-ajustes[^>]*data-str="errores\.irAjustes"')
        self.assertRegex(HTML, r'class="error-accion"\s+data-error-ajustes[^>]*hidden')

    def test_aparece_solo_con_errores_de_sesion(self):
        for codigo in ("requiere_sesion", "restriccion_edad",
                       "cookies_bloqueadas", "cookies_no_encontradas"):
            with self.subTest(codigo=codigo):
                self.assertIn('"%s"' % codigo, JS)
        self.assertIn('document.querySelector("[data-error-ajustes]")', JS)

    def test_lleva_a_la_pantalla_de_ajustes(self):
        self.assertIn('var irAjustes = document.querySelector("[data-error-ajustes]");', JS)
        self.assertRegex(JS, r'if \(irAjustes\) irAjustes\.addEventListener\("click",'
                             r'\s*function \(\) \{\s*mostrarPantalla\("ajustes"\)')


class BarraArrastrable(unittest.TestCase):
    """B6: arrastre con mouse, teclado, topes y conteo en pausa."""

    def test_el_asa_tiene_nombre_y_es_enfocable(self):
        self.assertRegex(HTML, r'class="barra-asa" data-arrastrar-barra role="button" '
                               r'tabindex="0"')
        self.assertIn("data-str-aria=\"barra.arrastrar\"", HTML)
        self.assertIn('"barra.arrastrar":', STRINGS)

    def test_usa_pointer_events_con_captura(self):
        for pieza in ("pointerdown", "pointermove", "pointerup", "pointercancel",
                      "setPointerCapture"):
            with self.subTest(pieza=pieza):
                self.assertIn(pieza, JS)

    def test_no_se_sale_de_la_ventana(self):
        self.assertIn("window.innerWidth - r.width", JS)
        self.assertIn("window.innerHeight - r.height", JS)
        self.assertIn("Math.min(Math.max(0, x), maxX)", JS)
        self.assertIn("Math.min(Math.max(0, y), maxY)", JS)

    def test_las_flechas_mueven_el_asa(self):
        for tecla in ("ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"):
            with self.subTest(tecla=tecla):
                self.assertIn('"%s"' % tecla, JS)
        self.assertIn("evento.shiftKey ? 40 : 10", JS)

    def test_se_reacota_al_cambiar_el_tamano(self):
        self.assertIn('window.addEventListener("resize", acotarBarra)', JS)

    def test_el_conteo_se_pausa_al_arrastrar(self):
        self.assertIn("pausarBarra();", JS)
        self.assertIn("programarBarra(restanteBarra);", JS)
        self.assertIn("Date.now() + restanteBarra", JS)

    def test_cada_barra_nueva_vuelve_al_origen(self):
        self.assertIn('barra.classList.remove("arrastrada")', JS)
        self.assertIn('barra.style.left = ""', JS)
        self.assertIn('barra.style.top = ""', JS)

    def test_la_x_sigue_cerrando(self):
        self.assertIn('data-cerrar-barra', HTML)
        self.assertIn('cerrar.addEventListener("click", ocultarBarraPortapapeles)', JS)

    def test_cursor_de_agarre_y_movimiento_reducido(self):
        self.assertRegex(CSS, r"\.barra-asa\s*\{[^}]*cursor: grab")
        self.assertRegex(CSS, r"\.barra-asa:active\s*\{[^}]*cursor: grabbing")
        self.assertRegex(CSS, r"\.barra-inferior\.arrastrada\s*\{[^}]*right: auto")
        self.assertRegex(
            CSS, r"@media \(prefers-reduced-motion: reduce\)\s*\{\s*\.barra-inferior\s*\{"
                 r"[^}]*transition: none")

    def test_la_barra_no_usa_una_variable_inexistente(self):
        self.assertNotIn("--esp-5", CSS)


class TamaniosFase9(unittest.TestCase):
    """B4 y B5: miniatura +35 % y MIAUK al doble, con escalones por altura."""

    def test_barra_con_los_tokens_nuevos(self):
        """23/10/2026: ×0,8 del doble (era 96/80/1040/72/52/44; el doble, 48/40/520/36/26/22).
        22/11/2026: -5% pedido por Maki (77→73, 64→61, 832→790).
        23/11/2026: recuadro 640×103 (-10% de alto sobre 114) con
        contenido -15%: botón 212×110, texto 1.2rem, X 42, asa 19,
        ícono 30.
        """
        t = tokens()
        self.assertEqual(t["--h-barra"].strip(), "103px")
        self.assertEqual(t["--h-input-barra"].strip(), "61px")
        self.assertEqual(t["--w-barra"].strip(), "640px")
        self.assertEqual(t["--h-miauk-barra"].strip(), "110px")
        self.assertEqual(t["--w-miauk-barra"].strip(), "212px")
        self.assertEqual(t["--x-barra"].strip(), "42px")
        self.assertEqual(t["--img-barra"].strip(), "36px")
        self.assertEqual(t["--ico-barra"].strip(), "30px")
        self.assertEqual(t["--asa-barra"].strip(), "19px")
        self.assertEqual(t["--fs-barra"].strip(), "1.2rem")

    def test_la_barra_nace_abajo_a_la_derecha(self):
        self.assertRegex(CSS, r"\.barra-inferior\s*\{[^}]*bottom: var\(--esp-4\)")
        self.assertRegex(CSS, r"\.barra-inferior\s*\{[^}]*right: var\(--esp-4\)")
        # Nada de anclaje arriba: la barra vive en la esquina inferior derecha.
        self.assertNotRegex(CSS, r"\.barra-inferior\s*\{[^}]*top:")

    def test_el_ancho_no_desborda_en_ventanas_angostas(self):
        # El recuadro se adapta a la frase (fit-content) con tope máximo.
        self.assertRegex(
            CSS, r"\.barra-inferior\s*\{[^}]*width: fit-content")
        self.assertRegex(
            CSS, r"\.barra-inferior\s*\{[^}]*max-width: min\(var\(--w-barra\),"
                 r" calc\(100vw - var\(--esp-4\) - var\(--esp-4\)\)\)")

    def test_arrastrada_se_suelta_de_las_dos_esquinas(self):
        self.assertRegex(CSS, r"\.barra-inferior\.arrastrada\s*\{[^}]*right: auto"
                              r"[^}]*bottom: auto")

    def test_miniatura_mas_grande(self):
        # Pedido Maki 08/11/2026: la vista previa se veía muy chica.
        ancho = int(tokens()["--w-mini"].strip().replace("px", ""))
        self.assertGreaterEqual(ancho, 200)

    def test_miauk_al_doble_con_escalones(self):
        # Ajustes 21/11: la barra detectora de enlaces se achicó 20 %
        # (152→122, 88→70, 48→38) y el campo de link 46→37.
        t = tokens()
        self.assertEqual(t["--h-btn-miauk"].strip(), "122px")
        self.assertEqual(t["--h-campo"].strip(), "37px")
        self.assertRegex(CSS, r"@media \(max-height: 760px\)[\s\S]{0,200}"
                              r"--h-btn-miauk: 70px")
        self.assertRegex(CSS, r"@media \(max-height: 640px\)[\s\S]{0,300}"
                              r"--h-btn-miauk: 38px")

    def test_el_compacto_conserva_su_miniatura(self):
        self.assertRegex(CSS, r"@media \(max-height: 760px\)[\s\S]{0,200}--w-mini: 168px")


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    unittest.main()

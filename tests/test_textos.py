# -*- coding: utf-8 -*-
"""Textos que la especificación fija literalmente (Fase 2D.1).

La fuente única de verdad es strings.es.js, pero estos textos no los elegí
yo: los fija la spec (DECISIONES.md §4, spec 2D Parte 0, spec 2D.1). Si
alguien los "mejora" por su cuenta, este test lo frena.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
STRINGS = RAIZ / "miauki" / "ui" / "js" / "strings.es.js"
HTML = RAIZ / "miauki" / "ui" / "index.html"

# Texto literal → dónde lo fija la spec
OBLIGATORIOS = {
    "paso1.titulo": "Pegá el link",                              # DECISIONES §4
    "paso1.analizar": "Analizar",                                # DECISIONES §4
    "paso1.ayuda": "cada click en MIAUK! agrega una descarga a la cola",  # DECISIONES §4 (Maki literal)
    "paso1.pegar": "Pegar del portapapeles",                     # spec 2D.1
    "paso3.mejor": "La mejor · 1080p",                           # pedido Maki 09/11/2026
    "paso3.equilibrada": "Equilibrada · 720p",                   # spec 2D Parte 0
    "paso3.liviana": "Liviana · 480p",                           # spec 2D Parte 0
    "col.fraseEntrada": "Sin vueltas, sin complicaciones, 100% amigable.",  # spec 2D.1
    "col.subsNo": "Subtítulos no disponibles",                   # referencia
    "col.subsIdiomas": "Disponibles:",                           # spec 3B (indicador de idiomas)
    "col.ariaColumna": "Guardar en y subtítulos",                # spec 2D.3 §1 (nombre de la columna)
    "col.cambiar": "Cambiar",                                    # spec 2D.3 §1a
    "col.abrirCarpeta": "Abrir carpeta",                         # spec 2D.3 §1a
    "col.incluirSubs": "Incluir subtítulos",                     # spec 2D.3 §1b
    "errores.vacio": "Pegá un link para analizar.",              # spec 3B (validación local)
    "errores.formato": "El link no es válido. Usá https://, http://, www. o un dominio con ruta (ej. minombre.io/video)",  # spec 3B / plan.md 3.4
    "errores.generico": "No pudimos analizar el link. Probá de nuevo.",  # spec 3B
    "paso2.foto": "foto",                                        # spec 3B (cantidad de fotos)
    "paso2.fotos": "fotos",                                      # spec 3B
    "paso3.foto": "Foto",                                        # spec 3B (opciones de imagen)
    "paso3.etiquetaFormato": "Formato:",                         # spec 3B (recuadro Info)
    "paso3.etiquetaTamano": "Tamaño:",                           # spec 3B
    "paso3.etiquetaTiempo": "Tiempo:",                           # spec 3B
    "barra.aviso": "Wow... un link: ¿Lo usamos?",                # DECISIONES §4 (spec manda sobre ref)
    "barra.miauk": "Miauk",                                      # DECISIONES §4
    # Fase 5C A4: texto principal, contacto y aviso legal (dictados por Maki)
    "acerca.gracias": ("Trasnochado, pensado y elaborado por Maki Ezequiel. "
                       "¡Espero que lo disfrutes mucho!"),
    "acerca.instagram": "@tusrecursosdigitaless",
    "apoyar.usdt": "Copiar dirección USDT",
    "apoyar.usdtRed": "USDT (TRC20):",
    "acerca.facebook": "Tus ReCursos Digitales",
    "acerca.facebookAria": "Abrir el Facebook de Tus Recursos Digitales",
    # Fase 6 B2: nombre accesible de la acción que NO borra el archivo
    "historial.accion.quitar": "Quitar del historial (no borra el archivo)",
    "historial.nota": "Quitar una descarga del historial no borra el archivo del disco.",
    "historial.accion.bajar": "Volver a bajar",
    "historial.accion.carpeta": "Abrir carpeta",
    "historial.accion.archivo": "Mostrar archivo",
    # Fase 7 B1: texto dictado para el interruptor y el aviso de formato
    "ajustes.compatibilidadNota": ("Videos que se abren en cualquier reproductor "
                                   "(hasta 1080p). Desactivalo para bajar en 4K/8K."),
    "paso3.avisoFormato": ("Este formato puede no abrirse en el reproductor de "
                           "Windows. Probá con VLC."),
    # Fase 8, 0.1: textos de jerga aprobados por Maki (22/10/2026)
    "cola.estado.interrumpida": "Quedó a medias",
    "cola.accion.reintentar": "Probar de nuevo la descarga",
    "ajustes.cookies": "Usar el inicio de sesión de tu navegador",
    "ajustes.ninguno": "No usar",
    "ajustes.fxtwitter": "Usar un respaldo para los links de X",
    "ajustes.fxtwitterNota": "Ayuda a ver fotos y videos de X sin cuenta.",
    "motor.versionIncluida": "Versión incluida",
    "motor.versionActualizada": "Versión actualizada",
    "motor.comprobado": "Revisado:",
}

# Palabras que Maki prohibió en la interfaz (Fase 8, decisión 0.1).
PROHIBIDAS = ("PyPI", "fxtwitter")

LEMA_LATERAL = "Las mejores descargas, siempre ♥"                # DECISIONES §5 (vive en el HTML)


class TextosObligatorios(unittest.TestCase):
    def _claves(self):
        js = STRINGS.read_text(encoding="utf-8")
        return dict(re.findall(r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', js))

    def test_los_textos_obligatorios_son_los_de_la_spec(self):
        claves = self._claves()
        for clave, esperado in OBLIGATORIOS.items():
            with self.subTest(clave=clave):
                self.assertIn(clave, claves, f"falta la clave '{clave}' en strings.es.js")
                self.assertEqual(claves[clave], esperado)

    def test_el_lema_lateral_vive_en_el_html(self):
        self.assertIn(LEMA_LATERAL, HTML.read_text(encoding="utf-8"))

    def test_ningun_texto_visible_usa_jerga_prohibida(self):
        """0.1: "PyPI" y "fxtwitter" no se muestran nunca."""
        for clave, valor in self._claves().items():
            with self.subTest(clave=clave):
                for palabra in PROHIBIDAS:
                    self.assertNotIn(palabra, valor)


class TextosEnIngles(unittest.TestCase):
    """09/11/2026: la interfaz arranca en inglés en una PC en inglés."""

    def _claves(self, ruta):
        js = ruta.read_text(encoding="utf-8")
        return dict(re.findall(r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', js))

    def test_el_archivo_ingles_existe_y_tiene_las_mismas_claves(self):
        es = self._claves(STRINGS)
        en = self._claves(STRINGS.parent / "strings.en.js")
        self.assertEqual(sorted(es), sorted(en))
        for clave, valor in en.items():
            with self.subTest(clave=clave):
                self.assertTrue(valor.strip(), f"'{clave}' está vacía en inglés")

    def test_el_html_carga_los_dos_idiomas_antes_de_app(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn("js/strings.en.js", html)
        self.assertLess(html.index("js/strings.en.js"), html.index("js/idioma.js"))
        self.assertLess(html.index("js/idioma.js"), html.index("js/app.js"))

    def test_la_calidad_mejor_se_traduce_the_best(self):
        en = self._claves(STRINGS.parent / "strings.en.js")
        self.assertTrue(en["paso3.mejor"].startswith("The Best"))


class TextosDeAppInfo(unittest.TestCase):
    """A4: los textos legales y de autoría son spec-lock y viven en app_info."""

    def test_autor_gracias_y_legal_exactos(self):
        from miauki import app_info
        self.assertEqual(app_info.AUTOR, "Maki Ezequiel")
        self.assertEqual(
            app_info.TEXTO_GRACIAS,
            "Trasnochado, pensado y elaborado por Maki Ezequiel. "
            "¡Espero que lo disfrutes mucho!")
        self.assertEqual(
            app_info.TEXTO_LEGAL,
            "Usá Miauki solo con contenido que tengas derecho a descargar. "
            "Ni Miauki YT ni Maki Ezequiel están afiliados con alguna red "
            "social. Miauki YT es un programa independiente; las marcas y "
            "nombres de las plataformas pertenecen a sus respectivos dueños "
            "y se mencionan solo con fines de compatibilidad.")
        self.assertEqual(app_info.ENLACES["instagram"],
                         "https://www.instagram.com/tusrecursosdigitaless/")

    def test_la_interfaz_usa_el_mismo_texto_de_gracias(self):
        from miauki import app_info
        js = STRINGS.read_text(encoding="utf-8")
        claves = dict(re.findall(r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', js))
        self.assertEqual(claves["acerca.gracias"], app_info.TEXTO_GRACIAS)


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    unittest.main()

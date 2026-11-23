# -*- coding: utf-8 -*-
"""Accesibilidad (Fase 2D.2): TODO elemento interactivo tiene una fuente de
nombre accesible en el HTML: texto visible, data-str/data-str-aria en él o en
sus hijos (app.js los inyecta), aria-label, aria-labelledby, placeholder, alt
o title.

Los textos de la interfaz llegan por JS, así que el chequeo de que el nombre
computado no queda vacío se hace también en la ventana real (ver reporte 2D.2);
acá se garantiza que NADIE publique un botón sin fuente de nombre, y que los
iconos <svg> dentro de botones queden ocultos (no duplican el nombre).
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HTML = RAIZ / "miauki" / "ui" / "index.html"
STRINGS = RAIZ / "miauki" / "ui" / "js" / "strings.es.js"

ETIQUETAS = {"button", "a", "input", "select", "textarea"}
ROLES = {"radio", "switch", "checkbox", "link", "button", "tab", "menuitem",
         "option", "slider"}
# Etiquetas sin cierre (HTML): no incrementan la profundidad
VOID = {"img", "input", "br", "hr", "meta", "link", "use", "source", "path"}


class Recolector(HTMLParser):
    """Registra cada interactivo con sus fuentes de nombre y sus svg."""

    def __init__(self):
        super().__init__()
        self.piezas = []          # dicts: tag, ident, fuentes, svgs_sin_ocultar
        self._prof = 0
        self._grab = None         # pieza en construcción

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self._grab is None:
            if tag in ETIQUETAS or a.get("role") in ROLES:
                self._grab = {
                    "tag": tag,
                    "ident": "%s%s" % (tag, " ." + a["class"] if a.get("class") else ""),
                    "fuentes": {},
                    "svgs": [],
                    "prof": self._prof,
                }
                self._sumar_fuentes(a)
                if tag in ("input", "select", "textarea"):
                    self._cerrar()
        else:
            if tag == "svg" and a.get("aria-hidden") != "true":
                self._grab["svgs"].append(tag)
            if tag == "img" and a.get("alt"):
                self._sumar_fuentes({"data-str": "", "texto": a["alt"]})
            self._sumar_fuentes(a)
        if tag not in VOID:
            self._prof += 1

    def handle_endtag(self, tag):
        if tag not in VOID:
            self._prof -= 1
        if self._grab is not None and self._prof <= self._grab["prof"]:
            self._cerrar()

    def handle_data(self, data):
        if self._grab is not None:
            self._sumar_fuentes({"texto": data})

    def _sumar_fuentes(self, a):
        f = self._grab["fuentes"]
        for clave in ("data-str", "data-str-aria", "aria-label",
                      "aria-labelledby", "placeholder", "title", "alt"):
            if a.get(clave):
                f[clave] = a[clave]
        if a.get("texto"):
            f["texto"] = (f.get("texto", "") + " " + a["texto"]).strip()

    def _cerrar(self):
        self._grab["fuentes"]["texto"] = " ".join(
            self._grab["fuentes"].get("texto", "").split())
        self.piezas.append(self._grab)
        self._grab = None


def recolectar():
    r = Recolector()
    r.feed(HTML.read_text(encoding="utf-8"))
    return r.piezas


class NombreAccesible(unittest.TestCase):
    def test_hay_interactivos(self):
        # 5 nav + campo + pegar + x + analizar + miauk + 6 radios card3
        # + btn-mas + 9 radios mas-opciones + barra (miauk, cerrar, input)
        self.assertGreaterEqual(len(recolectar()), 25,
                                "se perdieron interactivos del HTML")

    def test_todo_interactivo_tiene_fuente_de_nombre(self):
        sin_nombre = [p["ident"] for p in recolectar()
                      if not any(v.strip() for v in p["fuentes"].values())]
        self.assertEqual(sin_nombre, [],
                         "Interactivos sin fuente de nombre: %s" % sin_nombre)

    def test_las_claves_de_strings_existen(self):
        js = STRINGS.read_text(encoding="utf-8")
        faltantes = []
        for p in recolectar():
            for clave in (p["fuentes"].get("data-str", ""),
                          p["fuentes"].get("data-str-aria", "")):
                if clave and '"%s"' % clave not in js:
                    faltantes.append("%s -> %s" % (p["ident"], clave))
        self.assertEqual(faltantes, [], "Claves sin texto en strings: %s" % faltantes)

    def test_los_svg_de_botones_estan_ocultos(self):
        con_visibles = ["%s (svg sin aria-hidden)" % p["ident"]
                        for p in recolectar() if p["svgs"]]
        self.assertEqual(con_visibles, [],
                         "Iconos visibles que duplican el nombre: %s" % con_visibles)


class InterruptorSubs(unittest.TestCase):
    """2D.3 Parte 0 (A1): sin subtítulos el interruptor nace deshabilitado Y
    desmarcado, para que un lector de pantalla lo anuncie "desactivado, no
    marcado" y se vea apagado. actualizarSubs() (app.js) restaura el valor
    guardado cuando vuelven los subtítulos."""

    def test_nace_desmarcado_y_deshabilitado(self):
        import re
        html = HTML.read_text(encoding="utf-8")
        m = re.search(r"<input[^>]*role=\"switch\"[^>]*>", html)
        self.assertIsNotNone(m, "no está el interruptor de subtítulos")
        etiqueta = m.group(0)
        self.assertIn("disabled", etiqueta,
                      "el interruptor debe nacer deshabilitado (sin subs)")
        self.assertNotIn("checked", etiqueta,
                         "el interruptor debe nacer desmarcado (verse apagado)")


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    unittest.main()

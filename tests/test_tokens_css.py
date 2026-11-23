# -*- coding: utf-8 -*-
"""Guardia de tokens (Fase 9, 0.3): el CSS no puede inventar tokens ni medidas.

Dos reglas, las dos permanentes:

1. Todo `var(--algo)` que use cualquier CSS tiene que estar definido en
   `tokens.css`. Un token inexistente no rompe el CSS, así que se rompe acá:
   la propiedad se cae en silencio y nadie se entera.
2. Las medidas de la barra flotante viven solo en `tokens.css`. `layout.css`
   puede posicionarla y colorearla, pero no fijarle tamaños a mano (así el
   ajuste de "un quinto menos" del 23/10/2026 se hace en un solo lugar).

La búsqueda de `var()` se hace con expresiones regulares sobre el texto: no
hace falta un analizador de CSS de verdad para esto.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent
CSS = RAIZ / "miauki" / "ui" / "css"

TOKENS = CSS / "tokens.css"

# Propiedades que fijan tamaño de la barra. Las de posición/color no entran:
# cambiarlas no altera cuánto mide el aviso.
PROPIEDADES_TAMANO = {
    "width", "height", "min-width", "min-height", "max-height",
    "font-size", "gap", "row-gap", "column-gap",
}
_PROP_TAMANO = re.compile(
    r"^\s*(%s)\s*:\s*([^;]+);" % "|".join(sorted(p.replace("-", r"\-") for p in PROPIEDADES_TAMANO)),
    re.MULTILINE,
)
# Un número con unidad "fija" en el valor (0 y 0px no cuentan). vw/vh/% son
# relativos a la ventana, así que se permiten: no fijan un tamaño absoluto.
_LITERAL = re.compile(r"(?<![\w.-])(\d*\.?\d+)(px|rem|em)(?![\w-])")


def definidos() -> set[str]:
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", TOKENS.read_text(encoding="utf-8")))


def hojas() -> list[Path]:
    return sorted(CSS.glob("*.css"))


def bloques(texto: str):
    """(selector, cuerpo) de cada bloque, incluidos los de @media.

    Alcanza para este uso: los selectores internos de un @media no tienen
    llaves propias, así que el regex de `[^{}]+ {` los toma igual.
    """
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", texto):
        yield m.group(1).strip(), m.group(2)


class TokensDefinidos(unittest.TestCase):
    def test_todo_var_esta_en_tokens(self):
        conocidos = definidos()
        faltan = []
        for hoja in hojas():
            texto = hoja.read_text(encoding="utf-8")
            for nombre in re.findall(r"var\(\s*(--[a-z0-9-]+)", texto):
                if nombre not in conocidos:
                    faltan.append("%s: %s" % (hoja.name, nombre))
        self.assertEqual(faltan, [], "Tokens sin definir en tokens.css: %s" % faltan)

    def test_el_guardia_detecta_un_token_inventado(self):
        texto = ".x { color: var(--no-existe-nunca); }\n.y { gap: var(--esp-2); }"
        encontrados = re.findall(r"var\(\s*(--[a-z0-9-]+)", texto)
        self.assertIn("--no-existe-nunca", encontrados)
        self.assertNotIn("--no-existe-nunca", definidos())


class BarraSoloConTokens(unittest.TestCase):
    def _reglas_de_barra(self):
        # Solo la barra flotante del portapapeles: `.cola-barra` y
        # `.cola-progreso` son otra cosa (progreso de las descargas).
        for hoja in hojas():
            for selector, cuerpo in bloques(hoja.read_text(encoding="utf-8")):
                if re.search(r"\.barra-(inferior|asa|ico|aviso|input|miauk)", selector):
                    yield hoja.name, selector, cuerpo

    def test_la_barra_no_fija_tamanos_a_mano(self):
        problemas = []
        for nombre, selector, cuerpo in self._reglas_de_barra():
            for prop, valor in _PROP_TAMANO.findall(cuerpo):
                if _LITERAL.search(valor):
                    problemas.append("%s %s { %s: %s }" % (nombre, selector, prop, valor.strip()))
        self.assertEqual(problemas, [], "Medidas de la barra fuera de tokens.css: %s" % problemas)

    def test_los_tokens_de_la_barra_solo_se_definen_en_tokens_css(self):
        problemas = []
        for hoja in hojas():
            if hoja.name == TOKENS.name:
                continue
            for nombre in re.findall(r"(--[a-z0-9-]*barra[a-z0-9-]*)\s*:", hoja.read_text(encoding="utf-8")):
                problemas.append("%s define %s" % (hoja.name, nombre))
        self.assertEqual(problemas, [], problemas)

    def test_la_barra_tiene_sus_tokens(self):
        faltan = {"--h-barra", "--w-barra", "--h-input-barra", "--fs-barra",
                  "--ico-barra", "--img-barra", "--x-barra", "--asa-barra"} - definidos()
        self.assertEqual(faltan, set())


class EspCincoRetirado(unittest.TestCase):
    def test_no_queda_el_token_inexistente_esp_cinco(self):
        # Decisión 0.3: --esp-5 nunca existió y rompía la propiedad en silencio.
        for hoja in hojas():
            self.assertNotIn("--esp-5", hoja.read_text(encoding="utf-8"), hoja.name)
        self.assertNotIn("--esp-5", definidos())


if __name__ == "__main__":
    unittest.main()

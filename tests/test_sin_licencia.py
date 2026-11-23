# -*- coding: utf-8 -*-
"""Fase 9, A2: el programa es gratis. Que no vuelva ningún rastro de la venta.

Qué vigila (A2.1): el código de la app, la interfaz, los textos, `tools/`,
`tests/`, los archivos de la raíz (`app.py`, `requirements.txt`, `README.md`,
`.gitignore`, `*.spec`) y la documentación.
Qué NO vigila, a propósito:

- las licencias de TERCEROS (`miauki/LICENCIAS.txt`, `docs/LICENCIAS_TERCEROS.md`):
  son obligatorias y se quedan (A2.8 las revisa aparte);
- la historia de las decisiones (`docs/DECISIONES.md`, `docs/PENDIENTES.md`):
  ahí está escrito que la venta se revocó el 22/10/2026. El texto se conserva
  como historia y no viaja con el programa;
- este mismo archivo, que contiene los patrones prohibidos;
- `tools/generar_licencias.py` y `tools/build_exe.py`: hablan de la licencia de
  terceros en singular, que es correcto.

Sobre el `.exe` y el zip: si no existen, esos tests se saltean (una PC limpia
puede correr la suite sin haber compilado). Cuando existen, se revisan de
verdad: módulos del archivo PYZ y cadenas embebidas.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import re
import sys
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXE = RAIZ / "dist" / "Miauki YT.exe"
ENTREGA = RAIZ.parent / "Entrega"

CARPETAS = (RAIZ / "miauki", RAIZ / "tools", RAIZ / "tests")
SUELTOS = [RAIZ / "app.py", RAIZ / "requirements.txt", RAIZ / "README.md",
           RAIZ / ".gitignore"]
SUELTOS += sorted(RAIZ.glob("*.spec"))
SUELTOS += sorted(RAIZ.glob("*.cfg")) + sorted(RAIZ.glob("*.toml"))

EXCLUIDOS = {
    RAIZ / "miauki" / "LICENCIAS.txt",
    RAIZ / "tests" / "test_sin_licencia.py",
}

# Documentación de la historia: la revocación está escrita ahí a propósito.
DOCS_EXCLUIDOS = {
    RAIZ / "docs" / "DECISIONES.md",
    RAIZ / "docs" / "PENDIENTES.md",
    RAIZ / "docs" / "LICENCIAS_TERCEROS.md",
}

# (patrón, motivo). Se aplican línea por línea al código y a los textos.
PROHIBIDOS = (
    # La palabra "licencia" sola ya es legítima (la app declara GNU GPL 3.0);
    # lo prohibido son las frases de la venta que se revocó.
    (r"necesit[aá]s una licencia|licencia de prueba|\bclave de licencia\b"
     r"|\btu licencia\b", "texto de licencia de venta"),
    (r"DEMO_DESCARGAS", "contador de la demo"),
    (r"PyNaCl|pynacl|\bnacl\b|_sodium|libsodium", "PyNaCl (solo servía para las claves)"),
    (r"ES_DE_PRUEBA|MIAUKI_BUILD_PRUEBA", "candado de compilación de prueba"),
    (r"Versi[oó]n de prueba", "texto de versión de prueba"),
    (r"\bcomprar\b|\bprecio de venta\b", "enlace o texto de compra"),
    (r"MachineGuid", "huella de la máquina para la licencia"),
    (r"estado_licencia|activar_licencia|copiar_codigo_equipo", "API de licencia"),
    (r"clave_publica|claves_prueba|emitir_licencia|generar_claves_licencia"
     r"|probar_licencias", "herramientas de licencia"),
    (r"NO_APTO_PARA_VENDER|SOLO PRUEBA", "sello de la entrega de prueba"),
    (r"\bMKI[-_]", "código de equipo MKI"),
    (r"(?:demo|licencia)\.(?:json|dat)", "archivo de demo o licencia"),
)

# Solo en la app y la interfaz: la palabra "demo" en un test puede hablar de la
# maqueta del portapapeles, que no tiene nada que ver con la venta.
PROHIBIDOS_APP = ((r"\bdemo\b", "texto de demo comercial"),)


def archivos_vigilados():
    vistos = []
    for carpeta in CARPETAS:
        for ruta in carpeta.rglob("*"):
            if not ruta.is_file() or ruta in EXCLUIDOS:
                continue
            if "__pycache__" in ruta.parts:
                continue
            if ruta.suffix.lower() in (".py", ".js", ".html", ".css"):
                vistos.append(ruta)
    vistos.extend(r for r in SUELTOS if r.is_file())
    return vistos


def archivos_docs():
    return [r for r in (RAIZ / "docs").glob("*.md") if r not in DOCS_EXCLUIDOS]


def buscar_rastros(archivos, patrones=None):
    """Lista de (archivo, línea, motivo) para cada rastro prohibido."""
    patrones = list(patrones if patrones is not None else PROHIBIDOS)
    hallazgos = []
    for ruta in archivos:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        nombre = str(ruta.relative_to(RAIZ)) if RAIZ in ruta.parents else str(ruta)
        app = RAIZ / "miauki" in ruta.parents or str(ruta).startswith(str(RAIZ / "miauki"))
        for numero, linea in enumerate(texto.splitlines(), 1):
            for patron, motivo in patrones:
                ignorar = patron in (r"\bcomprar\b|\bprecio de venta\b",)
                if re.search(patron, linea, re.IGNORECASE if ignorar else 0):
                    hallazgos.append((nombre, numero, motivo))
                    continue
            if app:
                for patron, motivo in PROHIBIDOS_APP:
                    if re.search(patron, linea, re.IGNORECASE):
                        hallazgos.append((nombre, numero, motivo))
    return hallazgos


class SinRastrosDeVenta(unittest.TestCase):
    def test_no_queda_ningun_rastro_de_licencia_ni_venta(self):
        hallazgos = buscar_rastros(archivos_vigilados())
        self.assertEqual(
            [], hallazgos,
            "Quedó un rastro de la venta:\n" +
            "\n".join("%s:%s → %s" % (a, n, m) for a, n, m in hallazgos))

    def test_la_documentacion_no_quedaron_restos(self):
        """Docs: solo los vestigios que no pueden ser prosa (claves, sellos, MKI)."""
        duros = tuple((p, m) for p, m in PROHIBIDOS if m not in (
            "texto de licencia de venta",
            "enlace o texto de compra",
            "texto de demo comercial",
        ))
        hallazgos = buscar_rastros(archivos_docs(), duros)
        self.assertEqual([], hallazgos, hallazgos)

    def test_las_licencias_de_terceros_siguen(self):
        """No se llevó puesta la documentación legal que sí corresponde."""
        self.assertTrue((RAIZ / "miauki" / "LICENCIAS.txt").is_file())
        textos = (RAIZ / "miauki" / "ui" / "js" / "strings.es.js").read_text(
            encoding="utf-8")
        self.assertIn("Licencias de terceros", textos)

    def test_el_detector_encuentra_un_rastro_inventado(self):
        """Autochequeo: si el detector se rompe, este test lo delata."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            falso = Path(d) / "pepe.py"
            falso.write_text('CLAVE = "ES_DE_PRUEBA"\n', encoding="utf-8")
            hallazgos = buscar_rastros([falso])
        self.assertEqual(1, len(hallazgos))

    def test_el_detector_no_marca_licencias_de_terceros(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            legal = Path(d) / "legal.py"
            legal.write_text(
                'TEXTO = "Licencias de terceros: GPLv3"\n'
                'RUTA = "LICENCIAS.txt"\n', encoding="utf-8")
            self.assertEqual([], buscar_rastros([legal]))

    def test_el_detector_sigue_marcando_el_texto_de_la_venta(self):
        """La GPL usa la palabra "licencia"; la frase de la venta, no."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            venta = Path(d) / "venta.py"
            venta.write_text(
                'AVISO = "Para seguir usando Miauki necesitás una licencia."\n',
                encoding="utf-8")
            hallazgos = buscar_rastros([venta])
        self.assertEqual(1, len(hallazgos))


class LicenciasDeTercerosCompletas(unittest.TestCase):
    """A2.8: la documentación legal de terceros está completa y sin PyNaCl."""

    DEBEN_ESTAR = ("yt-dlp", "FFmpeg", "pywebview", "PyInstaller", "Python",
                   "Fredoka", "Caveat", "Simple Icons")

    def _texto(self):
        return (RAIZ / "miauki" / "LICENCIAS.txt").read_text(encoding="utf-8")

    def test_licencias_txt_nombra_a_todos(self):
        texto = self._texto().lower()
        faltan = [n for n in self.DEBEN_ESTAR if n.lower() not in texto]
        self.assertEqual([], faltan)

    def test_licencias_txt_no_nombra_pynacl_ni_libsodium(self):
        texto = self._texto().lower()
        for prohibido in ("pynacl", "libsodium", "nacl"):
            self.assertNotIn(prohibido, texto)

    def test_el_informe_de_licencias_cubre_lo_mismo(self):
        texto = (RAIZ / "docs" / "LICENCIAS_TERCEROS.md").read_text(encoding="utf-8")
        faltan = [n for n in self.DEBEN_ESTAR if n.lower() not in texto.lower()]
        self.assertEqual([], faltan)


class ExeSinLicencia(unittest.TestCase):
    """A2.2: el `.exe` no lleva módulos ni textos de licencia propia."""

    MODULOS_PROHIBIDOS = ("nacl", "sodium", "licencia", "demo_descargas")
    MODULOS_PERMITIDOS = ("packaging.licenses", "packaging.licenses._spdx")

    def setUp(self):
        if not EXE.is_file():
            self.skipTest("todavía no hay .exe compilado")

    def test_no_hay_modulos_de_cripto_de_licencia(self):
        from PyInstaller.archive.readers import CArchiveReader

        archivo = CArchiveReader(str(EXE))
        pyz = archivo.open_embedded_archive("PYZ.pyz")
        modulos = [m for m in pyz.toc if m not in self.MODULOS_PERMITIDOS]
        hallados = [m for m in modulos
                    if any(p in m.lower() for p in self.MODULOS_PROHIBIDOS)]
        self.assertEqual([], hallados)

    def test_no_hay_textos_de_venta_embebidos(self):
        datos = EXE.read_bytes().lower()
        for aguja in (b"demo_descargas", b"es_de_prueba", b"miauki_build_prueba",
                      b"clave_publica", b"claves_prueba", b"emitir_licencia",
                      b"machineguid", b"pynacl", b"_sodium", b"licencia.json",
                      b"demo.json", b"solo prueba", b"no_apto"):
            self.assertNotIn(aguja, datos, aguja.decode("ascii"))

    def test_la_interfaz_embebida_no_trae_restos(self):
        """La copia de la interfaz que viaja en el .exe no tiene vestigios.

        La igualdad "copia == repo" se comprueba al armar la entrega
        (tools/armar_entrega.py, `interfaz_igual_al_repo`): acá fallaría todo
        cambio de interfaz hasta recompilar.
        """
        from PyInstaller.archive.readers import CArchiveReader

        archivo = CArchiveReader(str(EXE))
        for clave in [k for k in archivo.toc if k.lower().endswith(("ui\\js\\app.js",
                                                                   "ui\\index.html"))]:
            texto = archivo.extract(clave).lower()
            for aguja in (b"demo_descargas", b"es_de_prueba", b"clave_publica",
                          b"licencia.json", b"comprar", b"solo prueba"):
                self.assertNotIn(aguja, texto, clave)

    def test_el_exe_coincide_con_la_interfaz_del_repo(self):
        """C7: si se cambió la interfaz y no se recompiló, la suite lo dice."""
        sys.path.insert(0, str(RAIZ / "tools"))
        from armar_entrega import interfaz_igual_al_repo

        self.assertEqual([], interfaz_igual_al_repo())


class ZipDeEntrega(unittest.TestCase):
    """A2.3: el zip que recibe la gente solo lleva el programa y sus licencias."""

    def setUp(self):
        zips = sorted(ENTREGA.glob("Miauki YT v*.zip"))
        if not zips:
            self.skipTest("todavía no hay zip en Entrega")
        self.ruta = zips[-1]

    def test_solo_lleva_el_exe_y_las_licencias(self):
        with zipfile.ZipFile(self.ruta) as paquete:
            nombres = sorted(paquete.namelist())
        self.assertEqual(["LICENCIAS.txt", "Miauki YT.exe"], nombres)

    def test_el_nombre_no_tiene_marcas_de_prueba(self):
        nombre = self.ruta.name.upper()
        for marca in ("SOLO PRUEBA", "NO APTO", "PRUEBA"):
            self.assertNotIn(marca, nombre)


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    unittest.main()

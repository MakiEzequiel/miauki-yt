# -*- coding: utf-8 -*-
"""Cartel suave cuando la app se traba (tanda 20/11/2026, paso 2).

El mecanismo vive en `miauki/ui/js/vigia.js` (sin DOM: recibe consultar() y
trabajando()). Acá se lo ejecuta de verdad con Node y timers reales cortos,
para probar los tres casos: se cuelga el puente (aparece), contesta siempre
(no aparece) y hay trabajo en curso (no aparece). El cableado de la interfaz
(botones, textos y llamada desde app.js) se verifica leyendo los archivos.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

UI = RAIZ / "miauki" / "ui"
VIGIA = UI / "js" / "vigia.js"
APP = UI / "js" / "app.js"
HTML = UI / "index.html"
STRINGS = UI / "js" / "strings.es.js"

GUION = r"""
const fs = require('fs');
eval(fs.readFileSync(process.env.VIGIA_JS, 'utf8'));

function correr(opciones) {
  return new Promise(function (resolver) {
    var avisos = 0;
    var vueltas = 0;
    var vigilante = globalThis.MiaukiVigia.crear(Object.assign({
      espera: 80,
      cada: 20,
      alAvisar: function () { avisos += 1; },
      alVolver: function () { vueltas += 1; }
    }, opciones));
    vigilante.iniciar();
    setTimeout(function () {
      vigilante.detener();
      resolver({ avisos: avisos, vueltas: vueltas });
    }, 400);
  });
}

function nuncaContesta() { return new Promise(function () {}); }

Promise.all([
  // Puente colgado: avisa una sola vez.
  correr({ consultar: nuncaContesta, trabajando: function () { return false; } }),
  // Puente sano: no avisa.
  correr({
    consultar: function () { return Promise.resolve({ ok: true }); },
    trabajando: function () { return false; }
  }),
  // Descargando o analizando: no avisa aunque no conteste.
  correr({ consultar: nuncaContesta, trabajando: function () { return true; } }),
  // Contesta tarde: avisa y se va solo al volver.
  correr({
    consultar: function () {
      return new Promise(function (ok) { setTimeout(ok, 200); });
    },
    trabajando: function () { return false; }
  })
]).then(function (r) {
  console.log(JSON.stringify(r));
});
"""


@unittest.skipUnless(shutil.which("node"), "hace falta Node para probar el JS")
class VigiaDeVerdad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        salida = subprocess.run(
            ["node", "-e", GUION],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "VIGIA_JS": str(VIGIA)})
        if salida.returncode != 0:
            raise AssertionError("node falló: " + salida.stderr)
        cls.casos = json.loads(salida.stdout.strip().splitlines()[-1])

    def test_si_el_puente_no_contesta_aparece_una_vez(self):
        self.assertEqual(self.casos[0]["avisos"], 1)

    def test_si_el_puente_contesta_no_aparece(self):
        self.assertEqual(self.casos[1]["avisos"], 0)

    def test_no_aparece_mientras_hay_trabajo_en_curso(self):
        self.assertEqual(self.casos[2]["avisos"], 0)

    def test_se_va_solo_cuando_el_puente_vuelve(self):
        # Contesta tarde (200 ms): aparece el cartel y, al volver el puente,
        # el aviso se retira solo sin recargar nada.
        self.assertGreaterEqual(self.casos[3]["avisos"], 1)
        self.assertGreaterEqual(self.casos[3]["vueltas"], 1)


class Cableado(unittest.TestCase):
    def setUp(self):
        self.html = HTML.read_text(encoding="utf-8")
        self.app = APP.read_text(encoding="utf-8")
        self.strings = STRINGS.read_text(encoding="utf-8")

    def test_el_cartel_tiene_refrescar_y_esperar(self):
        self.assertIn("data-traba hidden", self.html)
        self.assertIn("data-traba-refrescar", self.html)
        self.assertIn("data-traba-esperar", self.html)

    def test_los_textos_existen_en_los_dos_idiomas(self):
        en = (UI / "js" / "strings.en.js").read_text(encoding="utf-8")
        for clave in ("traba.texto", "traba.esperar"):
            self.assertRegex(self.strings, r'"%s":\s*"[^"]+"' % clave)
            self.assertRegex(en, r'"%s":\s*"[^"]+"' % clave)

    def test_refrescar_recarga_sin_perder_ajustes(self):
        self.assertIn('window.location.reload();', self.app)

    def test_el_vigia_existe_y_esta_cableado(self):
        self.assertTrue(VIGIA.exists())
        self.assertIn("js/vigia.js", self.html)
        self.assertIn("window.MiaukiVigia.crear(", self.app)
        self.assertIn("analisisEnCurso || activasCola > 0", self.app)


if __name__ == "__main__":
    unittest.main()

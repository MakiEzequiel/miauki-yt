# -*- coding: utf-8 -*-
"""Historial (Fase 6, B1): persistencia, tope, corrupción, privacidad."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import base64
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from miauki.core import history

PNG_1PX = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
           "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def datos(**extra):
    base = {
        "titulo": "Video de prueba",
        "sitio": "youtube",
        "tipo": "video",
        "calidad": "1080p",
        "contenedor": "mp4",
        "ruta": r"C:\Descargas\Video de prueba.mp4",
        "peso": 1234567,
        "url_canonica": "https://www.youtube.com/watch?v=abc123",
        "miniatura": PNG_1PX,
        "selector": "bestvideo[height<=1080]+bestaudio/best",
        "resolucion": 1080,
    }
    base.update(extra)
    return base


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="miauki_hist_"))
        self.ruta = self.dir / "historial.json"
        self.h = history.Historial(self.ruta)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _archivo(self):
        return json.loads(self.ruta.read_text(encoding="utf-8"))


class Persistencia(Base):
    def test_agrega_y_sobrevive_a_una_instancia_nueva(self):
        entrada = self.h.agregar(datos())
        self.assertTrue(entrada["id"])
        self.assertEqual(entrada["fecha"][-1], "Z")
        otro = history.Historial(self.ruta)
        lista = otro.listar()
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["titulo"], "Video de prueba")
        self.assertEqual(lista[0]["miniatura"], PNG_1PX)
        self.assertEqual(lista[0]["resolucion"], 1080)

    def test_la_mas_nueva_va_primero(self):
        self.h.agregar(datos(titulo="vieja"))
        self.h.agregar(datos(titulo="nueva"))
        self.assertEqual([e["titulo"] for e in self.h.listar()], ["nueva", "vieja"])

    def test_no_queda_temporal(self):
        self.h.agregar(datos())
        self.assertEqual(list(self.dir.glob("*.tmp")), [])

    def test_tope_de_500(self):
        for i in range(history.MAX_ENTRADAS + 5):
            self.h.agregar(datos(titulo=f"v{i}"))
        lista = self.h.listar()
        self.assertEqual(len(lista), history.MAX_ENTRADAS)
        self.assertEqual(lista[0]["titulo"], "v504")   # la última agregada
        self.assertNotIn("v0", [e["titulo"] for e in lista])

    def test_corrupcion_respalda_y_arranca_vacio(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        self.assertEqual(self.h.listar(), [])
        respaldos = list(self.dir.glob("historial.roto-*.json"))
        self.assertEqual(len(respaldos), 1)
        self.assertIn("esto no es json", respaldos[0].read_text(encoding="utf-8"))
        self.h.agregar(datos())
        self.assertEqual(len(self.h.listar()), 1)

    def test_concurrencia_de_la_cola(self):
        def trabajar(n):
            for i in range(5):
                self.h.agregar(datos(titulo=f"hilo {n} {i}"))
        hilos = [threading.Thread(target=trabajar, args=(n,)) for n in range(8)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(len(self.h.listar()), 40)


class Privacidad(Base):
    def test_quitar_borra_todo_rastro_del_archivo(self):
        entrada = self.h.agregar(datos(titulo="Secreto personal"))
        self.assertTrue(self.h.quitar(entrada["id"]))
        crudo = self.ruta.read_text(encoding="utf-8")
        for rastro in ("Secreto personal", entrada["id"], "iVBORw0KGgo"):
            self.assertNotIn(rastro, crudo)
        self.assertEqual(self.h.listar(), [])
        self.assertFalse(self.h.quitar(entrada["id"]))

    def test_borrar_vacia(self):
        for i in range(3):
            self.h.agregar(datos(titulo=f"t{i}"))
        self.assertEqual(self.h.borrar(), 3)
        self.assertEqual(self.h.listar(), [])
        self.assertNotIn("t1", self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(self.h.borrar(), 0)


class Validacion(Base):
    def test_rechaza_lo_que_no_sirve(self):
        self.assertIsNone(self.h.agregar({"tipo": "video"}))
        self.assertIsNone(self.h.agregar(datos(url_canonica="javascript:alert(1)")))
        self.assertIsNone(self.h.agregar(datos(tipo="archivo")))
        self.assertEqual(self.h.listar(), [])

    def test_miniatura_grande_se_descarta(self):
        grande = "data:image/png;base64," + base64.b64encode(b"x" * 350000).decode()
        entrada = self.h.agregar(datos(miniatura=grande))
        self.assertEqual(entrada["miniatura"], "")

    def test_miniatura_de_20kb_se_conserva(self):
        # Ajustes 21/11: el tope subió para que las vistas previas reales
        # queden guardadas en el historial.
        media = "data:image/png;base64," + base64.b64encode(b"x" * 20000).decode()
        entrada = self.h.agregar(datos(miniatura=media))
        self.assertEqual(entrada["miniatura"], media)

    def test_miniatura_que_no_es_imagen_se_descarta(self):
        entrada = self.h.agregar(datos(miniatura="data:text/html;base64,PHNjcmlwdD4="))
        self.assertEqual(entrada["miniatura"], "")

    def test_peso_invalido_queda_en_cero(self):
        self.assertEqual(self.h.agregar(datos(peso=-5))["peso"], 0)
        self.assertEqual(self.h.agregar(datos(peso=True))["peso"], 0)


if __name__ == "__main__":
    unittest.main()

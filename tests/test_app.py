# -*- coding: utf-8 -*-
"""El arranque siempre deja registro, incluso cuando se sale antes de la ventana."""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app


class SegundaInstancia(unittest.TestCase):
    def test_sale_con_0_y_se_registra_en_el_log(self):
        argv_previo = sys.argv[:]
        sys.argv = ["app.py"]
        try:
            with mock.patch.object(app, "instancia_unica", return_value=False):
                with self.assertLogs("miauki", level="INFO") as logs:
                    codigo = app.main()
        finally:
            sys.argv = argv_previo
        self.assertEqual(codigo, 0)
        self.assertTrue(
            any("Otra instancia" in m for m in logs.output),
            "La segunda instancia salió sin dejar registro en el log",
        )

    def test_todo_proceso_registra_su_inicio(self):
        argv_previo = sys.argv[:]
        sys.argv = ["app.py", "--version"]
        try:
            with self.assertLogs("miauki", level="INFO") as logs:
                app.main()
        finally:
            sys.argv = argv_previo
        self.assertTrue(
            any("Proceso iniciado" in m for m in logs.output),
            "Un arranque sin registro viola la regla de la Fase 1.1",
        )


class TamanoVentana(unittest.TestCase):
    """La ventana inicial nunca supera el 85% del área útil (condición de 2A)."""

    def test_pantalla_grande_abre_en_1420x840(self):
        # Área útil típica de 1920×1080 (con barra de tareas): no debe tocar nada
        self.assertEqual(app._tope_util(1420, 840, 1920, 1040), (1420, 840))

    def test_1366x768_encaja_en_el_85_por_ciento(self):
        # 1366×768 con barra ≈ 1366×728 de área útil → tope 1161×618
        self.assertEqual(app._tope_util(1420, 840, 1366, 728), (1161, 618))

    def test_solo_encaja_el_lado_que_excede(self):
        # 1400 de ancho útil → 1190 (encaja); alto 900 → 765 (840 no entra)
        self.assertEqual(app._tope_util(1420, 840, 1400, 900), (1190, 765))

    def test_nunca_supera_el_85_por_ciento(self):
        for util_w, util_h in [(1024, 640), (1366, 768), (2560, 1440)]:
            w, h = app._tope_util(1420, 840, util_w, util_h)
            self.assertLessEqual(w, int(util_w * 0.85))
            self.assertLessEqual(h, int(util_h * 0.85))


if __name__ == "__main__":
    unittest.main()

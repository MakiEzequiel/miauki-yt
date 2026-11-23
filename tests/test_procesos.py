# -*- coding: utf-8 -*-
"""Job Object: prueba REAL de que mata a los hijos de Miauki y a nadie más.

El proceso de prueba se mete en un job kill-on-close y crea dos hijos: uno
dentro del job y otro ajeno (creado antes de atar). Al cerrar el handle, el
propio proceso y su hijo mueren; el ajeno tiene que seguir vivo. Es la garantía
de que nunca hace falta matar `msedgewebview2.exe` por nombre.
"""
import apoyo  # noqa: F401  (aísla la carpeta de datos)
import ctypes
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

GUION = r'''
import json, subprocess, sys, time
sys.path.insert(0, r"{raiz}")
from miauki.core import procesos

ajeno = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
assert procesos.atar() is True
assert procesos.atar() is True          # idempotente
hijo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
print(json.dumps({{"hijo": hijo.pid, "ajeno": ajeno.pid}}), flush=True)
time.sleep(0.7)                          # deja que Windows asigne ambos al job
procesos.liberar()                       # cierra el job: mueren el guion y el hijo
time.sleep(5)                            # si sobreviviera, el test lo vería
'''


def _vivo(pid: int) -> bool:
    kernel32 = ctypes.windll.kernel32
    h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    codigo = ctypes.c_ulong()
    ok = kernel32.GetExitCodeProcess(h, ctypes.byref(codigo))
    kernel32.CloseHandle(h)
    return bool(ok) and codigo.value == 259  # STILL_ACTIVE


@unittest.skipUnless(sys.platform == "win32", "Job Objects son de Windows")
class JobObject(unittest.TestCase):
    def test_mata_a_los_hijos_y_respeta_a_los_ajenos(self):
        proceso = subprocess.run(
            [sys.executable, "-c", GUION.format(raiz=str(RAIZ))],
            capture_output=True, text=True, timeout=60,
        )
        datos = json.loads(proceso.stdout.strip().splitlines()[-1])
        time.sleep(1.0)
        self.assertFalse(_vivo(datos["hijo"]),
                         "el hijo dentro del job sobrevivió al cierre")
        try:
            self.assertTrue(_vivo(datos["ajeno"]),
                            "un proceso ajeno al job fue matado (prohibido)")
        finally:
            subprocess.run(["taskkill", "/PID", str(datos["ajeno"]), "/F"],
                           capture_output=True, check=False)


if __name__ == "__main__":
    unittest.main()

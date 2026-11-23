# -*- coding: utf-8 -*-
"""Job Object de Windows: los procesos hijos de Miauki mueren con Miauki.

Por qué: cuando la app se cierra a la fuerza, los renderers de WebView2
(`msedgewebview2.exe`) pueden quedar vivos y dejar bloqueado el perfil.
Matarlos por nombre sería un crimen: Teams, Outlook y Edge usan el mismo
proceso. La forma segura y exacta es un Job Object con
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`: Windows mata SOLO los procesos que
pertenecen al job (Miauki y sus descendientes) cuando se cierra el último
handle, incluso si el proceso murió de golpe.

Doc oficial (verificada 20/10/2026):
- CreateJobObjectW / SetInformationJobObject / AssignProcessToJobObject
  (learn.microsoft.com/windows/win32/procthread/job-objects)
- JOBOBJECT_EXTENDED_LIMIT_INFORMATION y
  JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE (winnt.h)
"""
import ctypes
import os
from ctypes import wintypes

from miauki.core.logger import obtener_logger

KILL_ON_JOB_CLOSE = 0x2000
EXTENDED_LIMIT_INFORMATION = 9
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001

_job = None  # el handle debe seguir abierto: al cerrarse, mata a los hijos


class _IoCounters(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def atar(pid: int | None = None) -> bool:
    """Mete este proceso (o `pid`) en un job kill-on-close. True si funcionó.

    Si Windows no lo permite (el proceso ya está en un job que no admite
    anidamiento), devuelve False y la app sigue: es una mejora, no un
    requisito para arrancar.
    """
    global _job
    if _job is not None:
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        obtener_logger().warning("No se pudo crear el Job Object (%s)",
                                 ctypes.get_last_error())
        return False
    info = _ExtendedLimits()
    info.BasicLimitInformation.LimitFlags = KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
            job, EXTENDED_LIMIT_INFORMATION, ctypes.byref(info),
            ctypes.sizeof(info)):
        obtener_logger().warning("No se pudo configurar el Job Object (%s)",
                                 ctypes.get_last_error())
        kernel32.CloseHandle(job)
        return False
    handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE,
                                  False, pid or os.getpid())
    if not handle:
        obtener_logger().warning("No se pudo abrir el proceso para el job (%s)",
                                 ctypes.get_last_error())
        kernel32.CloseHandle(job)
        return False
    ok = bool(kernel32.AssignProcessToJobObject(job, handle))
    kernel32.CloseHandle(handle)
    if not ok:
        obtener_logger().warning("No se pudo atar el proceso al job (%s)",
                                 ctypes.get_last_error())
        kernel32.CloseHandle(job)
        return False
    _job = job  # se suelta solo al morir el proceso
    obtener_logger().info("Job Object activo: los WebView2 de Miauki mueren con Miauki")
    return True


def liberar() -> None:
    """Cierra el handle del job (SOLO para pruebas en un proceso aparte)."""
    global _job
    if _job is not None:
        ctypes.WinDLL("kernel32").CloseHandle(_job)
        _job = None

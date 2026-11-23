# -*- coding: utf-8 -*-
"""Genera dist/Miauki YT.exe (PyInstaller onefile, 64 bits).

Paso 1: verifica el ffmpeg; si falla, NO se empaqueta.
Paso 2: verifica que no haya assets prohibidos en el proyecto.
Paso 3: PyInstaller con ícono, metadatos de app_info, la estructura de la
interfaz (index.html, css/, js/) y SOLO los assets listados en
tools/assets_manifest.txt (lista blanca, cierre de Fase 1).

Uso: python tools/build_exe.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import _entorno  # noqa: E402  (carpeta de datos temporal, nunca la real)

from miauki import app_info  # noqa: E402
from miauki.core.assets_check import leer_manifiesto, verificar_assets  # noqa: E402
from miauki.core.ffmpeg_tools import verificar_ffmpeg  # noqa: E402


def archivo_version() -> Path:
    """Metadatos que PyInstaller incrusta en el .exe (propiedades del archivo)."""
    d = RAIZ / "build"
    d.mkdir(exist_ok=True)
    f = d / "version_file.txt"
    v = app_info.VERSION_TUPLA
    f.write_text(
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        f"    filevers={v}, prodvers={v},\n"
        "    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable('040904B0', [\n"
        f"        StringStruct('CompanyName', '{app_info.AUTOR}'),\n"
        f"        StringStruct('FileDescription', '{app_info.DESCRIPCION}'),\n"
        f"        StringStruct('FileVersion', '{app_info.VERSION}'),\n"
        f"        StringStruct('InternalName', '{app_info.NOMBRE}'),\n"
        f"        StringStruct('OriginalFilename', '{app_info.NOMBRE_EXE}.exe'),\n"
        f"        StringStruct('ProductName', '{app_info.NOMBRE}'),\n"
        f"        StringStruct('ProductVersion', '{app_info.VERSION}'),\n"
        "      ])\n"
        "    ]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n",
        encoding="utf-8",
    )
    return f


def main() -> int:
    ok, msg = verificar_ffmpeg(RAIZ / "miauki" / "bin" / "ffmpeg.exe")
    print(msg)
    if not ok:
        print("BUILD DETENIDO: corrija el ffmpeg antes de empaquetar.", file=sys.stderr)
        return 1

    ok, msg = verificar_assets(RAIZ)
    print(msg)
    if not ok:
        print("BUILD DETENIDO: hay assets prohibidos en el proyecto.", file=sys.stderr)
        return 1

    # A5: LICENCIAS.txt se regenera en cada build. Si falta, NO se empaqueta.
    r = subprocess.run(
        [sys.executable, str(RAIZ / "tools" / "generar_licencias.py")], cwd=RAIZ)
    licencias = RAIZ / "miauki" / "LICENCIAS.txt"
    if r.returncode != 0 or not licencias.is_file():
        print("BUILD DETENIDO: falta miauki/LICENCIAS.txt (A5).", file=sys.stderr)
        return 1

    icono = RAIZ / "miauki" / "ui" / "assets" / "img" / "Icos" / "Miauki ico.ico"
    sep = ";"  # PyInstaller en Windows separa origen:destino con punto y coma

    # Estructura de la interfaz (siempre) + lista blanca de assets (manifiesto)
    add_data = [
        f"{RAIZ / 'miauki' / 'ui' / 'index.html'}{sep}miauki/ui",
        f"{RAIZ / 'miauki' / 'ui' / 'css'}{sep}miauki/ui/css",
        f"{RAIZ / 'miauki' / 'ui' / 'js'}{sep}miauki/ui/js",
        f"{RAIZ / 'miauki' / 'bin' / 'ffmpeg.exe'}{sep}miauki/bin",
        f"{RAIZ / 'miauki' / 'LICENCIAS.txt'}{sep}.",
    ]
    for rel in leer_manifiesto():
        origen = RAIZ / rel
        destino = Path(rel).parent  # misma estructura relativa dentro del .exe
        add_data.append(f"{origen}{sep}{destino}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", app_info.NOMBRE_EXE,
        "--icon", str(icono),
        "--version-file", str(archivo_version()),
    ]
    for d in add_data:
        cmd += ["--add-data", d]
    cmd += [
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
        "--exclude-module", "PySide2",
        "--exclude-module", "PySide6",
        "--exclude-module", "cefpython3",
        str(RAIZ / "app.py"),
    ]
    r = subprocess.run(cmd, cwd=RAIZ)
    if r.returncode == 0:
        exe = RAIZ / "dist" / f"{app_info.NOMBRE_EXE}.exe"
        # A5: la licencia viaja SIEMPRE junto al .exe (además de embebida).
        shutil.copy2(licencias, exe.parent / "LICENCIAS.txt")
        print(f"\nListo: {exe} ({exe.stat().st_size / 1024 / 1024:.1f} MB)")
        print(f"Licencias: {exe.parent / 'LICENCIAS.txt'}")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())

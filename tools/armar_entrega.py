# -*- coding: utf-8 -*-
"""Arma el paquete de prueba para Windows en la carpeta Entrega (Fase 8, 0.7).

El zip vivía en %TEMP% y Windows puede borrarlo. Se genera fuera del repo, en
`..\\Entrega\\`, así queda entre la carpeta del proyecto y no se pierde:

    python tools/armar_entrega.py

Contenido: `Miauki YT.exe` y `LICENCIAS.txt` (nada más), que es lo que recibe
quien prueba el programa. Si falta el `.exe`, avisa y no arma nada.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import _entorno  # noqa: E402,F401  (carpeta de datos temporal, nunca la real)

from miauki import app_info  # noqa: E402

DIST = RAIZ / "dist"
ENTREGA = RAIZ.parent / "Entrega"


def interfaz_igual_al_repo() -> list[str]:
    """Archivos de `miauki/ui/` que en el .exe no coinciden con el repo.

    Una copia vieja compilada antes del último cambio de interfaz se detecta
    acá, antes de repartir el zip (Fase 9, C7).
    """
    try:
        from PyInstaller.archive.readers import CArchiveReader
    except ImportError:
        print("aviso: sin PyInstaller no se compara la interfaz embebida")
        return []
    raiz = Path(__file__).resolve().parent.parent
    lector = CArchiveReader(str(DIST / (app_info.NOMBRE_EXE + ".exe")))
    problemas = []
    claves = [c for c in lector.toc if c.startswith("miauki\\ui\\")]
    for clave in claves:
        en_disco = raiz / clave.replace("\\", "/")
        if not en_disco.is_file():
            problemas.append("en el .exe y no en el repo: " + clave)
        elif hashlib.sha256(lector.extract(clave)).digest() != \
                hashlib.sha256(en_disco.read_bytes()).digest():
            problemas.append("distinto: " + clave)
    en_exe = {c.replace("\\", "/") for c in claves}
    for en_disco in (raiz / "miauki" / "ui").rglob("*"):
        if not en_disco.is_file() or en_disco.name.startswith("."):
            continue
        rel = en_disco.relative_to(raiz).as_posix()
        if rel not in en_exe:
            problemas.append("en el repo y no en el .exe: " + rel)
    return problemas


def main() -> int:
    exe = DIST / (app_info.NOMBRE_EXE + ".exe")
    licencias = DIST / "LICENCIAS.txt"
    for archivo in (exe, licencias):
        if not archivo.is_file():
            print(f"Falta {archivo}. Corré tools/build_exe.py primero.")
            return 1
    problemas = interfaz_igual_al_repo()
    if problemas:
        print("El .exe no coincide con la interfaz del repo:")
        for p in problemas[:20]:
            print("  " + p)
        print("Volvé a correr tools/build_exe.py antes de armar la entrega.")
        return 1
    print(f"interfaz embebida: idéntica al repo")
    ENTREGA.mkdir(parents=True, exist_ok=True)
    destino = ENTREGA / f"{app_info.NOMBRE} v{app_info.VERSION} - Windows.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.write(exe, exe.name)
        paquete.write(licencias, licencias.name)
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    print(f"paquete: {destino} ({destino.stat().st_size / 1048576:.1f} MB)")
    print(f"exe: {exe.stat().st_size / 1048576:.1f} MB")
    print(f"sha256 del exe: {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

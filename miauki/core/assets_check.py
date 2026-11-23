# -*- coding: utf-8 -*-
"""Lista negra de assets: el ícono viejo prohibido no puede existir ni usarse.

La única fuente de assets permitidos para el build es tools/assets_manifest.txt.
El ícono oficial es "Miauki ico.ico" (ver docs/DECISIONES.md).
"""
from pathlib import Path

# Concatenado a propósito: así este archivo no se detecta a sí mismo
PROHIBIDO_NOMBRE = "gatito" + "_neon_auriculares.ico"
PROHIBIDO_CLAVE = "gatito" + "_neon"

EXTENSIONES_REFERENCIA = {".py", ".html", ".css", ".js", ".json", ".spec", ".bat", ".ps1"}
# docs/ queda excluido: ahí viven la lista negra y el inventario histórico de la v2.6


def raiz() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def leer_manifiesto() -> list[str]:
    """Rutas relativas (con /) de los assets permitidos en el .exe."""
    manifiesto = raiz() / "tools" / "assets_manifest.txt"
    lineas = []
    for linea in manifiesto.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            lineas.append(linea)
    return lineas


def verificar_assets(base: Path | None = None) -> tuple[bool, str]:
    """False si el archivo prohibido existe o está referenciado en código."""
    base = base or raiz()
    malos = [
        p for p in base.rglob("*")
        if p.is_file() and PROHIBIDO_NOMBRE.lower() in p.name.lower()
        and ".git" not in p.parts
    ]
    referencias = []
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXTENSIONES_REFERENCIA:
            continue
        if ".git" in p.parts or "dist" in p.parts or "build" in p.parts:
            continue
        if p.relative_to(base).parts and p.relative_to(base).parts[0] == "docs":
            continue
        if p.name == "assets_check.py":
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if PROHIBIDO_CLAVE.lower() in texto.lower():
            referencias.append(p)

    if malos or referencias:
        partes = [f"Archivo prohibido presente: {p}" for p in malos]
        partes += [f"Referencia prohibida en código: {p}" for p in referencias]
        return False, "; ".join(partes)
    return True, "Sin archivos ni referencias al ícono prohibido"

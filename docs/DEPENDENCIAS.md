# Dependencias binarias — origen y verificación

Fecha: 12/10/2026
Este documento es la **única fuente de la verdad** sobre los binarios grandes del proyecto. `tools/verify_ffmpeg.py` compara contra el hash de acá.

---

## ffmpeg.exe (obligatorio para empaquetar)

| Campo | Valor |
|---|---|
| Archivo | `miauki/bin/ffmpeg.exe` |
| Peso | 105.423.872 B (100,5 MB) |
| Versión | `9.0.2-essentials_build-www.gyan.dev` (verificado con `ffmpeg -version` el 12/10/2026) |
| Tipo de build | **essentials**, estático, **64 bits**, licencia GPLv3 |
| Fuente oficial | Gyan Doshi — https://www.gyan.dev/ffmpeg/builds/ (sección "release builds") |
| Paquete del que salió | `ffmpeg-release-essentials.zip` (release 9.0.2 del 19/09/2026, 109 MB) |
| Cómo se obtuvo | Descargado en la sesión de la v2.6 del 10/03/2026 y copiado a la v1.0 el 12/10/2026 sin modificarlo |
| **SHA-256 del .exe** | `3256173F3F8BFFD7DF12227C68ADF68025EDB1832273A9530688A7BB1ED8EDEC` |

Notas verificadas en la página oficial (12/10/2026):
- "All builds are 64-bit, static and licensed as GPLv3".
- El hash que publica gyan.dev (`.sha256`) es del **paquete .zip**, no del .exe adentro; por eso el que documentamos y verificamos es el del `ffmpeg.exe` extraído, calculado en esta máquina.
- Requisito de la página oficial: Windows 10 o posterior.

### Verificación

```
python tools/verify_ffmpeg.py
```

Comprueba que el archivo exista y que su SHA-256 coincida con el de arriba. Sale con código 1 si falla.

### Reglas de uso

1. **Git**: `miauki/bin/*.exe` está en el `.gitignore` — el binario NUNCA se commitea (pesan 105 MB; GitHub rechaza >100 MB y cada build nuevo sumaría otro tanto).
2. **Build (Fase 1)**: el script de build en `tools/` DEBE correr `verify_ffmpeg.py` antes de empaquetar; si falla, el build se detiene con el mensaje en español que imprime el script.
3. **--selftest (Fase 1)**: debe incluir esta misma verificación y reportarla.
4. **Si falta el archivo**: re-descargar `ffmpeg-release-essentials.zip` desde https://www.gyan.dev/ffmpeg/builds/ y extraer solo `bin/ffmpeg.exe` a `miauki/bin/`.

---

## Assets gráficos de terceros — Simple Icons (Fase 2D)

| Campo | Valor |
|---|---|
| Archivos | `miauki/ui/assets/icons/{youtube,tiktok,instagram,facebook,x}.svg` (5 archivos) |
| Uso | Íconos de marca de la columna derecha (lista de sitios) |
| Fuente oficial | https://github.com/simple-icons/simple-icons |
| **Licencia** | **CC0 1.0 Universal (dominio público)** — verificada en https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md el 13/10/2026 |
| Modificación | Convertidos de `<svg>` standalone a `<symbol>` con `fill="currentColor"` (el patrón de este proyecto); paths sin tocar. |

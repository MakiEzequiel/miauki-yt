# JavaScript para YouTube: qué falta y cuánto costaría (Fase 8, 0.6)

Fecha: 22/10/2026. **Informe solamente: no se agregó nada al `.exe`.**
Decisión de Maki (Fase 8, punto 7): no ahora.

Fuentes oficiales consultadas:

- Wiki de yt-dlp: <https://github.com/yt-dlp/yt-dlp/wiki/EJS>
- Paquete en PyPI: <https://pypi.org/project/yt-dlp-ejs/> (JSON de PyPI: 0.8.0,
  rueda de 0,05 MB)
- Código instalado en esta PC: `yt_dlp/extractor/youtube/jsc/_builtin/ejs.py`
  (`_EJS_WIKI_URL`) y `yt_dlp/extractor/youtube/_video.py` (avisos exactos)
- Node.js: <https://nodejs.org/dist/index.json> (LTS 24.22.1, zip win-x64: 36,0 MB)
- Deno: <https://github.com/denoland/deno/releases> (v2.9.8, zip win-x64: 40,9 MB)

## 1. Qué es cada cosa, en simple

- **yt-dlp-ejs**: un paquete chico (0,05 MB) con los **scripts** que resuelven las
  "pruebas" que pone YouTube para complicar la descarga. No ejecuta nada por sí
  solo: son recetas en JavaScript.
- **Intérprete de JavaScript**: el programa que *ejecuta* esas recetas. yt-dlp
  usa **Deno** por defecto; también acepta Node.js, Bun y QuickJS, pero hay que
  habilitarlos a mano (`--js-runtimes`).
- Sin las dos cosas, YouTube entrega **menos formatos** (típicamente se cae la
  mejor calidad) y la extracción "sin JavaScript" ya está marcada como obsoleta.

## 2. Cuándo hace falta

Solo para **YouTube** (y derivados que usan el mismo mecanismo). Los demás
sitios (TikTok, Instagram, X, Facebook) no lo necesitan.

En la práctica: si un video de YouTube empieza a fallar o aparecen menos
calidades que antes, es la señal. Hoy, con yt-dlp 2026.8.19 y sin intérprete,
la app sigue funcionando; lo que se pierde son formatos.

## 3. Qué pesaría y qué complejidad sumaría

| Pieza | Tamaño | Nota |
|---|---|---|
| `yt-dlp-ejs` 0.8.0 | 0,05 MB (rueda) | scripts; licencia del proyecto yt-dlp |
| Node.js LTS 24.22.1 | **36,0 MB** (zip win-x64) | `node.exe` suelto es más grande al descomprimir |
| Deno 2.9.8 | **40,9 MB** (zip win-x64) | el que yt-dlp prefiere |

Traducido al `.exe`: pasaría de **84,0 MB a ~120 MB** (más el peso descomprimido),
y sumaría tiempo de arranque la primera vez que se usa.

Complejidad que agrega (por qué no es "solo copiar un archivo"):

1. Hay que **empaquetar un segundo ejecutable** dentro del onefile y decirle a
   yt-dlp dónde está (`--js-runtimes node:<ruta>`), porque no va a estar en el
   PATH del comprador.
2. Ese ejecutable se **descomprime en cada arranque** (PyInstaller onefile), lo
   que engorda el tiempo de inicio y el uso de disco temporal.
3. Más superficie para **falsos positivos de antivirus** (un `.exe` que lanza
   otro `.exe` desde `%TEMP%` es exactamente lo que miran).
4. **Mantenimiento**: los scripts de yt-dlp-ejs cambian junto con YouTube; hay que
   actualizar el paquete y el runtime, y probar de nuevo.
5. Licencias: MIT en ambos casos, compatibles; igual hay que sumarlas a
   `docs/LICENCIAS_TERCEROS.md` y a `LICENCIAS.txt`.

## 4. Qué error aparece cuando falta

Mensajes exactos del código de yt-dlp 2026.8.19:

- `WARNING: [youtube] No supported JavaScript runtime could be found. Only deno is
  enabled by default; to use another runtime add --js-runtimes RUNTIME[:PATH] …
  YouTube extraction without a JS runtime has been deprecated, and some formats
  may be missing.`
- `Signature solving failed: Some formats may be missing. Ensure you have a
  supported JavaScript runtime and challenge solver script distribution installed.`
- `n challenge solving failed: Some formats may be missing. …`

**Verificación en vivo (22/10/2026, esta PC):** el primer aviso se capturó tal
cual ejecutando `python -m yt_dlp --skip-download -F` sobre un link de YouTube.
Las consecuencias ("faltan formatos") están tomadas del código fuente y de la
wiki, **no** de una descarga fallida observada de punta a punta: el video de
prueba (`BaW_jenozKc`) ya no está disponible.

## 5. Qué hicimos igual (sin agregar nada al `.exe`)

`miauki/core/errors.py` mapea esos tres mensajes al código propio **`motor_sin_js`**
con un texto amable y el botón **"Buscar actualización"** (el mismo que usa
`motor_viejo`). Si algún día YouTube rompe la descarga por este motivo, Maki ve
una explicación en castellano en vez de un error técnico. Un test fija ese mapeo
(`tests/test_errors.py`, clase `JavaScriptParaYouTube`).

## 6. Si algún día se decide incluirlo

Orden barato y reversible:

1. Sumar `yt-dlp-ejs` a `requirements.txt` y al manifiesto del build (0,05 MB).
2. Empaquetar `node.exe` como binario adicional (`tool/motor/node.exe`) y pasarlo
   con `--js-runtimes node:<ruta>` desde `downloader.py`/`analyzer.py`.
3. Medir `.exe`, arranque en frío y caliente, y repetir la prueba en Windows 10.
4. Actualizar `LICENCIAS.txt`, `docs/LICENCIAS_TERCEROS.md` y esta página.

# Inventario de la v2.6 — qué hay, qué se lleva y qué se deja

Fecha: 12/10/2026
Fuente: `Documents\OPENCODE\contexto-miauki-completo.json` (historial completo) + exploración en solo lectura de la carpeta de la v2.6.

**Regla de oro: la carpeta de la v2.6 NO se modifica ni se borra nada. Es solo consulta.**

Carpeta de la v2.6: `C:\Users\Maki\Desktop\PROYECTOS\Miauki YT\Miauki YT MiMo 2.6 v2.6 OpenCode`

---

## 1. Qué tiene la v2.6

App de escritorio en Python 3.12 + CustomTkinter ( interfaz escritorio nativa de Python ), sin git, con estas piezas:

### Código (`src/`)
| Archivo | Qué hace |
|---|---|
| `src/main.py` | Punto de entrada + flags de prueba (`--selftest`, `--demo`, `--screenshot`, `--auto-url`, `--auto-download`) |
| `src/core/engine.py` | `probe()` analiza links; `build_choices()` arma calidades; `verify_sizes()` con HEAD; `format_size()` estima tamaños |
| `src/core/xengine.py` | ~24,6 KB: extractor de X/Twitter portado de cobalt (GraphQL + syndication + FxTwitter) |
| `src/core/direct.py` | Descarga directa por URL con progreso y cancelación (fotos/gif de X) |
| `src/core/jobs.py` | Cola secuencial 1-a-la-vez, subtítulos en 2da pasada, conversión gif con paleta |
| `src/core/ffmpeg.py` | Ubica ffmpeg embebido (`bundled_ffmpeg()`), `run()`, `to_gif()`, `remux()` |
| `src/core/store.py` | Carpeta de datos (`reg-miau`), ajustes.json, últimas 10 descargas |
| `src/core/utils.py`, `errors.py` | Utilidades y errores |
| `src/ui/app.py` | ~1958 líneas: toda la interfaz (dashboard, cards 1-2-3, cola, Ajustes, banner de portapapeles) |
| `src/ui/theme.py` | Paleta, tokens, botones, barras, chips |
| `src/ui/fondo.py` | Fondo nebulosa "maestro" con el banner pegado por Pillow |

### Assets (`assets/`) — los que se copiaron a la v1.0
- `fonts/`: Fredoka-{Regular,Medium,SemiBold}.ttf y Caveat-{Regular,Medium,SemiBold}.ttf (Caveat es la manuscrita) — **copiados**
- `bin/ffmpeg.exe` (ffmpeg 9.0.2 essentials, 105.423.872 B, 64 bits) — **copiado**
- `fondo_nebulosa.png` (1.687.589 B) — **copiado**
- `boton_miauk.png` + variantes `_hover/_press/_disabled`, `banner_header*.png`, `miauki.ico`, iconos PNG del gatito — NO copiados (la v1.0 usa el botón de Icos y sus propios assets; se pueden copiar después si hace falta)

### Build (`build/`)
`miauki.spec`, `build.ps1`, `version-info.txt` — PyInstaller onefile, console=False. El build de la v1.0 se escribe nuevo; esto es solo consulta.

### Estado
- Último .exe funcional: `Miauki YT.exe` de 73.568.440 B (70,2 MB), con ffmpeg embebido.
- El .exe NO tiene los cambios de UI del 10/10 (esos viven solo en el código fuente).
- Sin git, sin tests de regresión automatizados.

---

## 2. Qué se REUTILIZA (ya copiado en la v1.0)

19 archivos, verificados byte a byte (mismo tamaño que el original):

1. **Carpeta Icos completa** (11 archivos) → `miauki/ui/assets/img/Icos/`:
   - `Banner neón de Miauki transp.png` (1.229.616 B)
   - `Banner neón de MIAUKI.png` (1.033.681 B)
   - `Botón neón MIAUK! con huella.png` (214.639 B) ← **el botón MIAUK! de la interfaz**
   - `Botón-neón-MIAUK_con-huella ico.ico` (135.230 B)
   - `fondo nebulosa.png` (1.687.589 B)
   - `Idea de MIAUKI YT.jpeg` (163.724 B)
   - `Idea-de-MIAUKI-YT.png` (974.787 B) ← imagen de referencia del diseño
   - `Miauki ico.ico` (100.895 B)
   - `Miauki.png` (1.409.155 B)
   - `Miauki_ Gatos Kawaii y Neón Gaming ORIGI.png` (1.198.061 B)
   - `miauki_fondo_nebulosa_suave.png` (1.132.226 B)
2. **Fuentes** (6 archivos) → `miauki/ui/assets/fonts/`: Fredoka-Regular/Medium/SemiBold.ttf + Caveat-Regular/Medium/SemiBold.ttf
3. **`fondo_nebulosa.png`** de la v2.6 → `miauki/ui/assets/img/fondo_nebulosa.png`
4. **`ffmpeg.exe`** de 64 bits → `miauki/bin/ffmpeg.exe`
5. **Conocimiento** (se lee de la v2.6, no se copia código): trucos de yt-dlp, FxTwitter, cookies, subtítulos, merge — ver sección 4.

---

## 3. Qué se REHACE DESDE CERO y qué se DESCARTA

**Se rehace (código nuevo, inspirándose en el viejo pero sin copiarlo sin revisar):**
- Todo el backend: analizador, descargador de videos e imágenes, cola (ahora con pausa), historial, configuración, portapapeles, errores, logs.
- Todo el empaquetado (script de build nuevo).

**Se descarta:**
- Todo `src/ui/` (CustomTkinter): ya no hace falta.
- Los trucos de recortes de fondo de Pillow para el vidrio de Tk.
- Las dependencias de la v2.6 que la v1.0 no usa (customtkinter, pycryptodomex, brotli — estas dos últimas se reevalúan en la Fase 3).

---

## 4. Cómo descargaba imágenes la v2.6 (lo que hay que portar)

### X / Twitter (`xengine.py`, extractor propio)
- **GraphQL** `TweetResultByRestId` (queryId tomado de yt-dlp; el de cobalt daba 404).
- **Fallback syndication** (User-Agent de Googlebot + token).
- **Guest token** + cookies del navegador (`ct0`/`auth_token`).
- **Fallback FxTwitter** (`api.fxtwitter.com/status/<id>`) — solo si GraphQL y syndication fallan, controlado por el checkbox "usar FxTwitter si X no responde" (activado por defecto → esto pasa a ser un ajuste de la v1.0).
- **Parseo de URLs**: x.com, twitter.com, vxtwitter, fixvx, fxtwitter, twittpr; `/video/N`, `/photo/N`, `/mediaviewer`, `/i/bookmarks`.
- **Media**: foto, video, gif, voz, picker (posts con varias imágenes), retweet.
- **Aviso importante**: los metadatos de X mienten ~3x → verificar el tamaño real con `HEAD` antes de mostrarlo.
- Descargas de fotos/gif van por `direct.py` (descarga directa con progreso y cancelación), no por el flujo normal de yt-dlp.

### Facebook
- **Sin código propio**: iba por el extractor `FacebookIE` de yt-dlp (su URL valida `photo.php`).
- En la v1.0: mantener eso y probar con links reales (Fase 3).

### Reglas heredadas que siguen valiendo
- YouTube trae `filesize: null` → estimar `tbr × duración / 8`.
- Video ≥480p con fallback; audio 320/256/128 kbps (YouTube entrega ~128 nativo; 256/320 re-codifican).
- GIF: bajar mp4 y convertir aparte con paleta (nunca escribir encima del mp4).
- Subtítulos es/en como 2da pasada best-effort (evita HTTP 429).
- Merge de video+audio con ffmpeg.
- Cookies: Ninguna/Chrome/Firefox/Edge + archivo `cookies.txt` Netscape (Edge falla por DPAPI → exportar con "Cookies.txt" de Firefox: https://addons.mozilla.org/es-ES/firefox/addon/cookies-txt/).

---

## 5. Decisiones heredadas del JSON de contexto que manda la spec de la v1.0

- Cola **1 a la vez** (secuencial), hasta 10 en espera — ahora además con pausa.
- Motor: yt-dlp como librería de Python + ffmpeg embebido.
- Extractores X nativos en Python (NO Node embebido, NO API remota).
- Interfaz 100% offline, sin CDNs.
- Datos del usuario en `%LOCALAPPDATA%\Miauki YT\` (la v2.6 usaba `MiaukiYT` — la v1.0 usa el nombre nuevo con espacio) o `reg-miau` junto al .exe si hay `portable.flag`.
- Errores amables en español; trazas técnicas solo al log.
- UI y textos en español rioplatense (voseo).

---

## 6. Gotchas técnicos de la v2.6 que conviene tener presentes

- **PowerShell 5.1**: sin `&&` (usar `;`), sin heredocs; acentos/emojis en comandos inline rompen el parser → scripts `.py` en `%TEMP%\opencode\` y listados escritos a archivo antes de leerlos.
- **GUIs**: lanzar con `Start-Process -Wait -PassThru` (el `&` directo no espera).
- **Visor de imágenes de opencode** trae contenido cruzado: leer PNGs de a uno por turno y con nombres nuevos.
- **Sesiones de opencode** viven en `C:\Users\Maki\.local\share\opencode\opencode.db` (SQLite, solo lectura).
- **Rebuild de la v2.6** (solo si algún día hiciera falta, no debe): `powershell -ExecutionPolicy Bypass -File build\build.ps1` con el .exe cerrado.

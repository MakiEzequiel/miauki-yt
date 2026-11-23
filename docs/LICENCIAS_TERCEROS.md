# Licencias de terceros — Miauki YT v1.0

Fecha: 20/10/2026. Fuentes verificadas ese día en la documentación oficial de cada proyecto (los enlaces están en cada ficha). Este informe responde una sola pregunta: **qué viaja dentro del `.exe` que se entrega y qué obliga cada licencia**.

El `.exe` es un `--onefile` de PyInstaller: adentro van el intérprete de Python, las librerías de Python, la interfaz completa (HTML, CSS, JS, fuentes, íconos, imágenes) y `ffmpeg.exe`. O sea: **todo lo de la tabla se redistribuye con la app**, salvo el runtime de WebView2, que lo instala Microsoft.

## Resumen

| Componente | Versión | Qué es | Licencia | Cómo viaja | Obligación al distribuir | ¿Bloquea? |
|---|---|---|---|---|---|---|
| ffmpeg | 9.0.2 essentials (gyan.dev) | binario que corta/une audio y video | **GPLv3** | dentro del `.exe` | texto GPLv3 + ofrecer el código fuente correspondiente | No, pero hay que cumplirlo |
| yt-dlp | 2026.8.19 | extrae links (librería) | **Unlicense** (dominio público) | dentro del `.exe` | ninguna | No |
| pywebview | 6.2.1 | ventana con WebView2 | **BSD 3-Clause** | dentro del `.exe` | aviso de copyright + texto BSD | No |
| pythonnet | 3.2.1 | puente Python/.NET (lo usa pywebview) | **MIT** | dentro del `.exe` | aviso + texto MIT | No |
| clr-loader | 0.3.1 | carga del runtime .NET (lo usa pythonnet) | **MIT** | dentro del `.exe` | aviso + texto MIT | No |
| bottle | 0.13.4 | servidor local de pywebview | **MIT** | dentro del `.exe` | aviso + texto MIT | No |
| proxy-tools | 0.1.0 | utilidad de pywebview | **MIT** | dentro del `.exe` | aviso + texto MIT | No |
| Python | 3.12 | intérprete | **PSF-2.0** | dentro del `.exe` | incluir el texto de la licencia PSF | No |
| PyInstaller | 6.22.3 | empaquetador | **GPL 2.0 + excepción** | su bootloader, dentro del `.exe` | ninguna: la excepción permite empaquetar y distribuir sin crédito | No |
| Fredoka (3 pesos) | — | tipografía de la interfaz | **OFL 1.1** | dentro del `.exe` | copyright + texto OFL; no venderla sola | No |
| Caveat (3 pesos) | — | tipografía manuscrita | **OFL 1.1** | dentro del `.exe` | copyright + texto OFL; no venderla sola | No |
| Íconos de marcas | — | YouTube, TikTok, Instagram, Facebook, X | **CC0 1.0** (Simple Icons) | dentro del `.exe` | ninguna | No |
| Marcas y logos | — | los mismos dibujos | **marcas registradas** de cada empresa | dentro del `.exe` | uso nominativo: identificar el sitio; no insinuar respaldo | No |
| WebView2 Runtime | 153.0.4234.48 | motor del navegador | propietario de Microsoft | **no se empaqueta**: lo instala Microsoft | ninguna | No |
| Banner, fondo, ícono | — | arte del proyecto | del autor (Maki) | dentro del `.exe` | ninguna | No |

**Conclusión corta: nada bloquea distribuir ni vender la app.** Lo único que falta es un archivo de licencias en el paquete (ver checklist al final).

## Ficha por componente

### ffmpeg — el único con una obligación real

- **Build exacto** (verificado con `ffmpeg -version` el 20/10/2026):
  `ffmpeg version 9.0.2-essentials_build-www.gyan.dev`, con `--enable-gpl --enable-version3`, `libx264` y `libx265` en la configuración.
- **Por qué GPLv3**: el build incluye `libx264` y `libx265`, que son GPL, y declara `--enable-gpl --enable-version3`. La página oficial de gyan.dev lo dice textual: *"All builds are 64-bit, static and licensed as GPLv3"* (verificado el 20/10/2026 en <https://www.gyan.dev/ffmpeg/builds/>).
- **Cómo lo usa la app**: se ejecuta como **proceso separado** (`subprocess`), nunca se enlaza con el código Python. Eso es "agregación" en términos de la GPL: la app **no** se vuelve GPL por incluirlo.
- **Obligaciones**:
  1. Entregar el **texto completo de la GPLv3** junto con el binario.
  2. Ofrecer el **código fuente correspondiente** (ffmpeg 9.0.2 y las librerías de ese build). Alcanza con indicar por escrito de dónde bajarlo; gyan.dev publica el commit exacto del release: <https://github.com/FFmpeg/FFmpeg/commit/946fcce07b>.
  3. No agregar restricciones sobre el ffmpeg que se entrega.
- **Hash y origen del archivo**: ver `docs/DEPENDENCIAS.md` (SHA-256 del `ffmpeg.exe` y cómo se obtuvo).

### Fuentes: Fredoka y Caveat

- Ambas bajo **SIL Open Font License 1.1**. Copyright verificados en el repositorio oficial de Google Fonts:
  - Fredoka: *"Copyright 2016 The Fredoka Project Authors (https://github.com/hafontia/Fredoka-One)"*
  - Caveat: *"Copyright 2014 The Caveat Project Authors (https://github.com/googlefonts/caveat)"*
- **Obligación**: cada copia de la app tiene que llevar el aviso de copyright y el texto de la OFL (basta un archivo de licencias legible). No se pueden vender las fuentes por separado, y una versión modificada no puede usar el nombre original. Acá no se modificaron los archivos `.ttf`.

### pywebview y sus dependencias

- **pywebview 6.2.1 — BSD 3-Clause**, copyright *"2014-2017, Roman Sirokov"*. La BSD exige reproducir el aviso de copyright, la lista de condiciones y el descargo **en la documentación o los materiales que acompañan la distribución binaria**. En una app de escritorio, eso se cumple con el archivo de licencias del paquete.
- **pythonnet 3.2.1, clr-loader 0.3.1, bottle 0.13.4, proxy-tools 0.1.0 — MIT**: mismo criterio (aviso + texto MIT).
- Se verificaron las licencias en los metadatos instalados (`importlib.metadata`) y en los archivos `LICENSE` de los repositorios oficiales.

### Python

- El intérprete que PyInstaller mete en el `.exe` es **Python 3.12, licencia PSF-2.0**. Hay que incluir su texto (es corto) en el archivo de licencias.

### PyInstaller

- **GPL 2.0 con excepción**. La página oficial (<https://pyinstaller.org/en/stable/license.html>) dice textual que los bundles generados se pueden distribuir *"with whatever license you want"* y que **no** hace falta incluir la licencia de PyInstaller ni darle crédito. No impone nada.

### yt-dlp

- **Unlicense** (dominio público). Sin obligaciones. Se usa como librería, no como programa aparte.

### Íconos de marcas

- Los 5 SVG salen de **Simple Icons**, licencia **CC0 1.0** (dominio público). Está documentado con fuente y fecha en `docs/DEPENDENCIAS.md`, y fueron convertidos a `<symbol>` sin tocar los paths.
- Aparte de la licencia del dibujo, los logos son **marcas registradas** de YouTube/Google, TikTok/ByteDance, Meta (Instagram y Facebook) y X Corp. Usarlos para identificar el sitio del que se descarga es uso nominativo razonable; lo que no se puede es sugerir que la app está respaldada por esas empresas.

### WebView2

- El runtime **no viaja** en el `.exe`: si falta, la app lo descarga del instalador oficial de Microsoft (fwlink 2124703, firma verificada; ver `docs/DECISIONES.md`). Microsoft lo distribuye con sus propios términos; acá no se redistribuye.

### Arte propio

- Banner, fondo y el ícono `.ico` son del proyecto (Maki). El ícono se regeneró a partir del original con su OK (ver `docs/DECISIONES.md`). No hay licencia de terceros involucrada.

## Checklist para poder distribuir

Nada de esto bloquea la venta; son tareas de cumplimiento, todas de una sola vez:

1. **`LICENCIAS.txt`** junto al `.exe` (o dentro del instalador) con: GPLv3 completa, OFL 1.1 con los dos avisos de copyright, BSD de pywebview, MIT de pythonnet/clr-loader/bottle/proxy-tools y PSF de Python.
2. **En "Acerca de"**: un enlace visible a ese archivo y la indicación de dónde está el código fuente de ffmpeg.
3. Nada más. No hay componentes con licencias incompatibles ni con obligaciones de pago.

> Para la Parte B (B4, "Acerca de") conviene dejar el texto y el enlace ya previstos, así el cumplimiento queda dentro de la app y no depende de un archivo suelto que el usuario puede borrar.

## Cómo se verificó

- `ffmpeg -version` sobre `miauki/bin/ffmpeg.exe` (build, flags de GPL y librerías).
- `importlib.metadata` para versión y licencia declarada de cada paquete instalado.
- Lectura de los `LICENSE` oficiales de pywebview, clr-loader y yt-dlp, y de los `OFL.txt` de Fredoka y Caveat en el repositorio de Google Fonts.
- Lectura de la página de licencia de PyInstaller y de la página de builds de gyan.dev.

# Decisiones del proyecto — Miauki YT v1.0

Fecha: 12/10/2026
Origen: especificación completa del usuario (prompt "PROYECTO: MIAUKI YT v1.0 — RECREACIÓN COMPLETA DESDE CERO") + respuestas a las 2 dudas de arranque.
Este documento manda sobre cualquier sugerencia de una skill: si una skill propone algo distinto (React, Tailwind, shadcn, otra estructura, otro empaquetado), se ignora y se avisa.

---

## 1. Dudas resueltas al arrancar

1. **Reportes**: UN reporte por fase (sección 1 del prompt manda): al terminar cada fase, frenar, reportar y esperar OK antes de seguir.
2. **Backend**: REESCRIBIR de cero (secciones 2 y 7 del prompt). La frase "sin tocar parte de la lógica" = NO tocar la carpeta de la v2.6 (queda intacta, solo consulta). El backend de la v1.0 se escribe nuevo usando el conocimiento de la v2.6 como referencia.

## 2. Decisiones técnicas cerradas (no se discuten)

- Backend: **Python 3.12 de 64 bits**.
- Interfaz: **pywebview + HTML/CSS/JS vanilla** (sin frameworks, sin Node, sin npm, sin build de frontend). Motor forzado `gui='edgechromium'` (Edge/WebView2); nunca el motor viejo de IE.
- App **NATIVA .exe** de Windows: no se abre en el navegador, no Electron, no servidor visible.
- **Requisito duro**: correr en Windows 10/11 de 64 bits sin instalar nada (ni Python, ni ffmpeg, ni runtimes). Todo embebido en el .exe, con la única excepción del runtime de WebView2.
- **WebView2 Runtime NO se empaqueta**. Se detecta al arrancar (verificar método por registro en la doc oficial de Microsoft); si falta, la app baja sola el Evergreen Bootstrapper oficial, lo ejecuta en modo silencioso y se reabre; sin internet → mensaje claro en español.
- Si junto al .exe existe la carpeta `ui` con un `index.html` válido, se usa ESA (probar cambios sin regenerar el .exe); si no, la embebida (y se deja constancia en el log). Resuelto en `paths.py`; `--selftest` informa cuál se usa.
- Descargas: **yt-dlp como librería** + ffmpeg embebido (64 bits).
- Empaquetado: **PyInstaller onefile** de 64 bits con ícono y metadatos. En la Fase 9 se mide arranque y se evalúa onedir; no decidir antes.
- Interfaz **100% offline**: fuentes, íconos, fondo e imágenes dentro de la app. Prohibido CDN/Google Fonts. Miniaturas las baja Python.
- Ventana: marco normal de Windows, **redimensionable** desde todos los bordes, maximizable, con tamaño mínimo.
- Datos del usuario en `%LOCALAPPDATA%\Miauki YT\`; nunca escribir en la carpeta del programa ni en la temporal del onefile. Todas las rutas en `paths.py`. Con archivo `portable.flag` vacío junto al .exe → datos en `reg-miau` junto al .exe.
- Sin dependencias innecesarias: cada librería nueva se justifica.
- **ffmpeg.exe fuera de Git (12/10/2026)**: `miauki/bin/*.exe` está en el `.gitignore`; el binario de 105 MB NO se commitea (infla el repo para siempre y GitHub rechaza >100 MB). Origen oficial, versión y SHA-256 documentados en `docs/DEPENDENCIAS.md`. El build y el `--selftest` deben correr `tools/verify_ffmpeg.py` antes de empaquetar y detenerse con mensaje en español si falla. (Queda pendiente, con OK del usuario, limpiar el binario de los commits viejos — ver sección 10.)
- **Ícono oficial de la app**: `Miauki ico.ico` de la carpeta Icos (100.895 B). **PROHIBIDO** usar `gatito_neon_auriculares.ico` (el de la v2.6).

## 2b. Lista negra de assets y flujo de WebView2 (cierre de Fase 1, 12/10/2026)

- **Ícono prohibido**: `gatito_neon_auriculares.ico` (78.626 B, gatito de neón rosa del primer boceto, guardado en "Miauki YT BACK UP\assets\" y embebido en los .exe de la v2.6). **PROHIBIDO en todo el proyecto v1.0**: ni ícono del .exe, ventana, interfaz, build, ni documentación de uso. La única fuente de assets permitidos para el .exe es `tools/assets_manifest.txt` (lista blanca UTF-8).
- **Cómo se hace cumplir**: `miauki/core/assets_check.py` (`verificar_assets()` y `leer_manifiesto()`), invocado por `--selftest` y por `tools/build_exe.py` (detiene el build). `tests/test_assets.py` verifica: (a) el archivo prohibido no existe en el árbol (excluye `.git`), (b) no hay referencias en código `.py/.html/.css/.js/...` fuera de `docs/` (donde vive esta lista negra), (c) el `.exe` generado no lo contiene (vía `pyi-archive_viewer --list`).
- **Ícono oficial (resuelto 13/10/2026)**: el `Miauki ico.ico` original de `Icos\` solo tenía 256 px; con OK del usuario se regeneró el del proyecto partiendo de `Miauki.png` (1254×1254, LANCZOS + unsharp en ≤32 px), con 7 entradas PNG: 16, 24, 32, 48, 64, 128, 256. Verificado a mano (nitidez 16/24/32), en la barra de título, en la barra de tareas y en el .exe regenerado. El original de `Icos\` quedó intacto como referencia.
- **WebView2 — Windows mínimo del conjunto**: Windows 10 versión **1709** (Fall Creators Update) o posterior, según la doc oficial de Microsoft (learn.microsoft.com/microsoft-edge/webview2/concepts/distribution, verificada 12/10/2026). El Runtime Evergreen preinstalado llegó en 1803+ (Nov 2022 update), pero la app instala el Bootstrapper oficial si falta, así que el piso real es 1709+.
- **WebView2 — flujo B implementado** (`miauki/core/webview2.py`): detección por clave de registro `{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` (pv ≠ 0.0.0.0) en HKLM WOW6432Node y HKCU; si falta, descarga `MicrosoftEdgeWebview2Setup.exe` (~1.9 MB) por urllib con validación de host (solo `*.microsoft.com` y `*.dl.delivery.mp.microsoft.com`, HTTPS, URL final tras redirección incluida), verifica firma Authenticode con WinVerifyTrust (API nativa, sin shell), ejecuta `/silent /install` con `subprocess` (shell=False, timeout 600 s), re-detecta y borra el descargado siempre. Sin internet o con firma inválida → mensaje en español + `MessageBoxW`. La app no avanza si WebView2 no queda disponible.
- **Escenarios de prueba**: la variable `MIAUKI_TEST_WEBVIEW2` fuerza `falta`, `exito`, `sin-internet` o `firma-mala` (nunca en uso normal; `tests/test_webview2.py` los cubre).
- **Servidor interno de pywebview (verificado 12/10/2026)**: la app pasa la ruta **plain** (sin `file://`) a `create_window`; así pywebview levanta su servidor HTTP interno con estas garantías (inspección de fuente + prueba empírica con la ventana corriendo):
  - Escucha **solo en 127.0.0.1** (bottle con host por defecto `127.0.0.1`; comprobado con `netstat`/`Get-NetTCPConnection`: `127.0.0.1:puerto`, sin `0.0.0.0`; desde la IP de red local la conexión se rechaza).
  - Sirve **solo la carpeta de la interfaz** (`miauki/ui` o la `ui` externa): `root_path = commonpath` de las URLs locales. `/index.html` → 200; `/app.py`, `/../app.py`, `/..%2f..%2fapp.py` → 403/404 (traversal bloqueado por `bottle.static_file`); `/css/`, `/js/`, `/assets/fonts/` → 404 (**sin listado de directorios**); `/` → 500 vacío (ruta que la app no usa; la ventana carga `/index.html`).
  - Sin caché (`Cache-Control: no-store`). Nota: si se pasara `file://`, pywebview **no** levanta servidor (la página se leería del disco directo); la ruta plain es la configuración soportada y más restrictiva.
- **Carrera de `pywebviewready` (bug corregido 12/10/2026)**: pywebview despacha el evento en `window` (ver `webview/js/finish.js`), NO en `document`; escuchar en `document` nunca lo recibe. Además `pywebview.api` existe como objeto vacío antes de cargar los métodos. `whenReady(cb)` en `miauki/ui/js/bridge.js` resuelve ambas cosas (chequea `api.ping` y escucha en `window`) y es la puerta de entrada de todas las fases. **Cualquier llamada al API debe pasar por `whenReady`.**

## 2c. Fase 2A — app shell (13/10/2026)

- **Grilla**: 3 filas `clamp(h-encabezado) minmax(0,1fr) auto` + áreas lateral/encabezado/central/derecha/inferior. Todas las medidas viven en `tokens.css` (nada hardcodeado en `layout.css`).
- **Bug raíz de la barra inferior (corregido)**: un `7%` dentro del `height` de un ítem NO resuelve durante el sizing de la grilla (el alto del contenedor aún no está definido), así que la fila `auto` se dimensionaba con solo el borde (2px) y la barra se desbordaba 46px hacia abajo, cortada por el borde de la ventana. Solución: token `--h-inferior: clamp(48px, 7vh, 64px)` — **regla: en `height` de ítems usar `vh`/`vw`, nunca `%`**. (En `grid-template-rows` el `%` sí resuelve y está bien, como en `--h-encabezado`.)
- **`min-height: 0` en las zonas de la grilla** (`.barra-lateral`, `.columna-derecha`, `.central`): sin eso, el contenido intrínseco de la zona infla la fila flexible y desborda la ventana entera. Las fases 2B+ que llenen zonas deben mantenerlo.
- **Sin tope de ancho en `.central`**: se probó un cap de 1100px y a 1920 desalineaba el encabezado respecto de las tarjetas; se eliminó. La referencia existe solo a 1600 y ahí la columna llena su pista igual.
- **Barra colapsable**: `.app.sin-inferior` pone la altura del ítem en 0 y la fila `auto` la sigue (por eso `vh` y no una fila fija); el espacio libre lo absorbe la columna central.
- **Verificación de interfaz**: Edge headless con perfil aislado (`--user-data-dir` propio; sin él, Edge delega el lanzamiento en la ventana abierta y no escribe el screenshot) + sonda pywebview (rectángulos, toggles, `backdrop-filter` real) + PrintWindow para capturas de ventana sin robar foco.

## 2d. Fase 2B ajustes (aprobados, 13/10/2026)

- **Banner**: se usa `Banner neón de Miauki este OK.png` (2158×729, PNG con transparencia; byte a byte igual al viejo "transp"). Los dos banners viejos salieron del proyecto con `git rm` (siguen en el historial). `object-fit` NO se declaró: la regla escala por alto (`max-height` + `height: auto`, centrado) — `cover` cortaría logo, tagline y gato de las esquinas. Los `.png` decorativos van en el manifiesto de assets (`tools/assets_manifest.txt`) porque Windows los firma/empaqueta; un test nuevo en `tests/test_ui.py` falla si un asset referenciado por HTML/CSS no está en el manifiesto.
- **Header de marca**: `.marca-lateral` vive fuera del `<nav>` (no es un ítem de navegación; es identidad de producto). Cápsula con borde `--borde-vidrio` + fondo `--nav-hover`. Gatito = `Miauki.png` a 34px (no existe gato a línea en Icos, avisar al usuario). **Interruptor = token `--marca-lateral`** (`flex`/`none`): apagado con evaluate_js en la sonda, quita el header sin dejar huecos. Compacto <1000px: solo gatito (`.marca-nombre { display:none }`).
- **Contraste magenta**: `--degradado-fin` pasó de `#c026d3` a `#ad1fc0` (contraste sobre el fondo violeta oscuro 4.04 → 4.83:1, AA para texto grande; 4.83 es la píldora "Inicio").
- **`--w-sidebar`**: de `clamp(120px, 10.5%, 175px)` a `clamp(140px, 11.9%, 190px)` — 190px = ancho de la sidebar en el mock a 1600, y con eso "Acerca de..." entra en UNA línea (verificado en captura `marca_con_1600x939.png`).
- **Métricas de ancho del logo (aviso, no fix)**: a 1200 el texto "Miauki YT" se parte en dos líneas dentro de la cápsula (la sidebar mide ~141px) — entra sin desbordar; no se achica la fuente.

## 2e. Fase 2D.2 — decisiones de Maki (14/10/2026, cambio aprobado por Maki)

Estas decisiones MODIFICAN la especificación anterior. Mandan sobre cualquier texto previo de este documento o de los PENDIENTES.

1. **Banner (cambio aprobado por Maki)**: queda EXACTAMENTE como está (centrado y grande, sin ocupar todo el ancho). Descartado el banner modular: NO analizar ni proponer partirlo.
2. **Tarjeta de marca "Miauki YT" de la barra lateral (cambio aprobado por Maki)**: se QUITA (repite el banner). El espacio sobrante se redistribuye con los mismos tokens.
3. **Columna derecha (cambio aprobado por Maki)**: se QUITA la lista de sitios (YouTube, TikTok, Instagram, Facebook, X, +1800 sitios más) porque repite los íconos del banner. En su lugar va un panel nuevo "Guardar en" + subtítulos (solo aspecto, datos de demo).
4. **PENDIENTES (cambio aprobado por Maki)**: quedan CERRADAS como decisiones tomadas la tarjeta de marca, las reglas de calidad (sección 5 de este documento) y el contenido de "Más opciones". Sigue abierta SOLO la del aviso "Wow... un link" (spec vs referencia): no cambiarla.

### 5b. Reglas de calidad (cambio aprobado por Maki, 14/10/2026 — la lógica real se programa en la Fase 3)

- **Mejor** = la resolución más alta disponible (hasta 8K).
- **Equilibrada** = 1080p si la resolución máxima disponible es de 1440p o más; si no, 720p; si no existe un punto medio real, no se muestra.
- **Liviana** = la menor resolución disponible de 480p o más; si el video original es menor a 480p, la menor disponible.
- Si dos opciones coinciden, se muestra una sola.
- **"Más opciones"**: lista de TODAS las calidades reales disponibles, ordenadas de mayor a menor, cada una con su peso estimado; en Música: 320 / 256 / 128 kbps.


La del prompt (sección 4), con 2 mejoras justificadas:
- `miauki/bin/` para el ffmpeg (105 MB; la estructura no decía dónde iba).
- `miauki/ui/assets/img/Icos/` para la carpeta Icos completa con sus nombres originales.

## 2f. Fase 2D.3 — decisiones de Maki (14/10/2026, aprobado por Maki)

Estas decisiones MODIFICAN la especificación anterior. Mandan sobre cualquier texto previo de este documento o de los PENDIENTES.

1. **Panel derecho "Guardar en" + subtítulos (aprobado por Maki)**: SÍ se implementa en Inicio. Es el MISMO dato que Ajustes (carpeta de descargas, subtítulos es/en): **una única fuente de verdad en la configuración**; Inicio solo lo muestra y lo cambia, sin duplicar estado en la interfaz. Punto de entrada documentado en esta sección y en PENDIENTES (f). "Descarga en curso" NO se hace ahora: candidata de la Fase 5, anotada en PENDIENTES.
2. **Alturas bajas 618 y 560 (aprobado por Maki)**: dos ajustes SOLO para alturas bajas: (a) ocultar la ayuda "cada click en MIAUK! agrega una descarga a la cola" y conservar esa información como descripción accesible del botón MIAUK! (aria-describedby y/o title); (b) bajar el alto del botón MIAUK! manteniendo su proporción. El banner NO se toca. Objetivo: selector de calidad visible sin scroll a 618; si aún faltan píxeles, reportar cuántos y proponer el siguiente ajuste sin achicar el banner.
3. **Aviso de la barra (aprobado por Maki)**: decisión CERRADA — se mantiene "Wow... un link: ¿Lo usamos?" (la spec manda). Cerrada también en PENDIENTES.
4. **"Acerca de..." entre 1200 y 1279 px (aprobado por Maki)**: debe quedar en UNA línea (ajuste por token).
5. **Reglas de calidad (aprobado por Maki)**: `miauki/core/formats.py` es la **ÚNICA fuente** de las reglas §5b (con sus 8 pruebas). La demo de JavaScript es descartable y la interfaz real recibirá las opciones desde Python en las fases siguientes. **No duplicar las reglas en JavaScript** más allá de esa demo.
6. **Textos nuevos del panel (spec 2D.3 §1d)**: `col.ariaColumna` = "Guardar en y subtítulos" (nombre accesible de la columna), `col.rutaDemo` = "Descargas\Miauki YT" (ruta de demo; si no entra en la columna se abrevia por el medio), `col.cambiar` = "Cambiar", `col.abrirCarpeta` = "Abrir carpeta", `col.incluirSubs` = "Incluir subtítulos". Están en strings.es.js y cubiertos por tests/test_textos.py.
   - **Punto de entrada (panel)**: la configuración es la única fuente de verdad (carpeta de descargas + subtítulos), igual que en Ajustes. La interfaz solo la refleja: la Fase 6 sincronizará `config` → `#col-subs-incluir` al iniciar y `#col-subs-incluir` → `config` al cambiar, y conectará "Cambiar"/"Abrir carpeta" (hoy solo aspecto). En la demo (sin config) el HTML nace deshabilitado y desmarcado (`disabled`, sin `checked`), porque el video de ejemplo no tiene subtítulos; el valor guardado en la configuración se conserva aparte (en JS, no en el DOM) y se restaura cuando el interruptor se habilita (ajuste A1 de la Parte 0 de 2D.3).
   - **Estado deshabilitado de subtítulos**: con `data-subs="no"` el interruptor queda visible PERO deshabilitado y desmarcado (opacidad `--op-deshab`, `checked=false`, para no mentir a lectores de pantalla) y debajo sigue la fila existente "Subtítulos no disponibles" (la fila funciona como la explicación del estado deshabilitado); con `data-subs="si"` el interruptor está activo y la fila se oculta. El cambio lo hace `MiaukiUI.actualizarSubs(disponible)` (único punto de entrada).
7. **Claves de la lista de sitios borradas (Parte 0 de 2D.3, aprobado por Maki 15/10/2026)**: `col.youtube`, `col.tiktok`, `col.instagram`, `col.facebook`, `col.x` y `col.sitiosMas` quedaron sin uso desde que la lista se quitó (punto 3 de §2e): se eliminaron de `js/strings.es.js` y de `tests/test_textos.py`. La lista de sitios en sí ya estaba descartada.
8. **"Acerca de..." con la ventana por defecto (Parte 0 de 2D.3, aprobado por Maki)**: el punto 4 aplica también al viewport de ~1184 px (ancho del viewport de la ventana por defecto del .exe): 1 línea desde 1184 hasta 1600, logrado con menos padding en los ítems de la barra lateral (sin agrandar `--w-sidebar` ni la ventana).

## 3. Fase 3B — decisiones de Maki (15/10/2026, aprobado por Maki)

Estas decisiones MODIFICAN la especificación anterior. Mandan sobre cualquier texto previo de este documento o de los PENDIENTES.

1. **Fotos de Facebook — link 6 (aprobado por Maki)**: usar el mensaje específico "Las fotos de Facebook todavía no se pueden analizar". Además INVESTIGAR en solo lectura cómo las resolvía la v2.6 (Maki recuerda que descargaba imágenes de Facebook; el inventario decía que lo hacía yt-dlp, pero yt-dlp 2026.08.19 no tiene extractor): leer el código de la v2.6 sin tocarlo y, si se puede, ejecutar su lógica de forma aislada con el link 6 y otros tipos de links de Facebook (publicaciones con fotos, share/p, photo.php, álbumes). Reportar qué tipos funcionaban y por qué vía. NO implementar nada nuevo todavía.
2. **Runtime de JavaScript de YouTube — A8 (aprobado por Maki)**: opción (b), dejar como está por ahora. Queda en `docs/PENDIENTES.md` con prioridad ALTA (el README de yt-dlp lo marca como necesario para soporte completo). Cuando Maki pase un link de YouTube en 4K u 8K, repetir la comparación con y sin runtime para ver si faltan formatos; la decisión se toma en la Fase 8.
3. **Videos verticales (aprobado por Maki)**: usar el lado corto como resolución (un reel de 1080×1920 es "1080p"), tanto en las etiquetas como para aplicar las reglas de calidad §5b.
4. **Scroll de 49 px en la ventana por defecto del .exe (aprobado por Maki)**: eliminarlo aplicando, en este orden y parando cuando el scroll llegue a 0: (a) el título del video en la tarjeta 2 a UNA línea con puntos suspensivos y el título completo como tooltip, (b) menos separación entre tarjetas, (c) menos margen. El banner no se toca; la ventana por defecto no cambia de tamaño.
5. **1 px de scroll en anchos ≤640 (aprobado por Maki)**: aprobado, separador lateral de 12 a 8 px.
6. **Cookies (aprobado por Maki)**: sin explicación en la interfaz por ahora (se hace en la Fase 6 con Ajustes real). Los mensajes de error de "requiere iniciar sesión" deben mencionar "Ajustes → Cookies".

## 3b. Fase 3B Parte B — decisiones de implementación (16/10/2026)

Registradas al conectar el análisis real a la interfaz; respaldadas por la verificación en ventana real y en el .exe.

1. **CSP `img-src 'self' data:`**: las miniaturas/fotos del análisis son data-URIs (`analyzer._resultado_imagenes` las convierte; las que no se pueden bajar se descartan). La CSP no abre la red: ninguna URL del análisis se carga como imagen.
2. **Validación local en JS**: vacío y "no empieza con https://" se resuelven en la interfaz con textos `errores.*` (sin llamar al motor); todo lo demás lo resuelve Python.
3. **Descarte de respuesta vieja por contador `nLanzamiento`**: el gate A3 impide dos análisis en vuelo; `id_solicitud` queda como marca del contrato, no como chequeo extra.
4. **Panel Info**: etiquetas `paso3.etiqueta*` + valor real; "Peso total descargado: —" hasta la Fase 4.
5. **MIAUK!**: se habilita tras un análisis OK (listo=true) y su clic no hace nada hasta la Fase 4.
6. **Sitios en la tarjeta 2**: mapa `SITIOS` en app.js (YouTube/Instagram/Facebook/X/TikTok); sitio + duración formateada ("3:09", "—" si null).
7. **Tipo Imagen en el selector**: las opciones son radios "Foto 1..n"; el panel Info queda en "—".
8. **Estado inicial real**: el .exe nacía con el link demo y "Me at the zoo" (maqueta de Fase 2); ahora nace vacío: input vacío, tarjeta 2 "Pegá un link y tocá Analizar…", ruta real de los ajustes.
9. **Scroll ventana por defecto**: (a)+(b)+(c) aplicados → 49→23 px; el resto (23 px) espera decisión de Maki (PENDIENTES (b)).

## 3c. Fase 4 Parte 0 — cierre de la 3B (16/10/2026, aprobado por Maki)

Instrucciones de Maki (16/10/2026) y decisiones tomadas al ejecutarlas:

1. **Estabilidad — instrumentación permanente**: `app.py` activa `faulthandler` (pila ante crash nativo → `faults.log`), `sys.excepthook` (excepción no capturada), `threading.excepthook` (excepción en hilo, por nombre), `atexit` (salida de Python sin crash) y log de cierre ("webview.start volvió tras Ns" + "Proceso finaliza con código N"). Con eso se distingue: cierre normal / crash / excepción.
2. **Estabilidad — hallazgos de la investigación**: en 30 días de Visor de eventos de Windows NO hay ni un evento 1000 (crash) de "Miauki YT", python ni msedgewebview2; sí un 1001 RADAR_PRE_LEAK_64 de msedgewebview2 (4/10/2026, crecimiento de memoria, no crash) a monitorear. La "app que se cerró sola" NO se reprodujo en la prueba larga (≥30 min de uso real). Hallazgos operativos: (a) `Stop-Process` de las sesiones de pruebas anteriores y/o `Start-Process -WindowStyle Hidden` dejaban la app sin ventana nativa — para pruebas, lanzar con `python.exe` + `Start-Process` sin Hidden; (b) el remote debugging de pywebview (puerto 9333) no se abre con `pythonw.exe`.
3. **Facebook**: investigación de la v2.6 ejecutada aislada (ver PENDIENTES (b)): **la v2.6 tampoco resolvía fotos** (foto/photo.php/share/p/álbum → "Unsupported URL"; permalink → "Cannot parse data"; solo `share/r/` funciona porque es video). Propuesta de vía propia con cookies anotada en PENDIENTES; **sin implementar, espera OK de Maki**.
4. **Scroll ventana por defecto**: eliminados los 23 px restantes con la opción menos invasiva pedida — separación central 8→4, pisos de tarjeta vacía 150/148→144/142, relleno de tarjeta 8→6 (solo `@media (max-height: 760px)`; banner y tamaño de ventana intactos). **Scroll = 0 medido** en 1200×720, 1355×721 y 1600×900.
5. **Interruptor de subtítulos**: verificado en DOM (sin cambios de código): con subs → `disabled=false, checked=true` (default del ajuste); usuario lo apaga; video sin subs (reel IG) → `disabled=true, checked=false` + aviso visible; vuelve un video con subs → `disabled=false, checked=false` (**se restaura el valor del usuario**, no el default).
6. **Insignia de la Cola de Descargas**: el "3" del HTML de maqueta quitado (`hidden` inicial); la Fase 4 lo mostrará vía `MiaukiUI.actualizarCola`.

## 3d. Fase 4 Parte B — decisiones de implementación (16/10/2026, aprobado por Maki)

Plan de la Parte B aprobado por Maki ("Continue", 16/10/2026): corre completo
(B1–B7) sin esperar OK intermedio; el freno es solo con el REPORTE FINAL.

1. **Orden**: B1 decisiones → B2 `core/downloader.py` → B3 `core/queue_manager.py` → B4 puente/eventos → B5 conexión mínima UI (MIAUK!, `MiaukiUI.actualizarCola`, módulo receptor de eventos, Cambiar/Abrir carpeta) → B6 pruebas (ventana y .exe con ffmpeg embebida) → B7 commits chicos.
2. **Selector de formatos**: la calidad elegida ya viene resuelta del análisis (`selector` por opción: `avc1`+`mp4a` → mp4; si no, mejor combo con contenedor real mp4/mkv — decisión 3B 0b d). El descargador usa ese `selector` tal cual con `merge_output_format` = `contenedor` de la opción. **Sin re-codificar video.**
3. **Música**: `selector: bestaudio` + postproceso MP3 con el kbps elegido (320/256/128). **Imagen**: descarga directa de la URL del snapshot (misma vía de análisis, sin red extra).
4. **Snapshot al encolar**: al tocar MIAUK! la UI manda el ítem completo de una (url_canónica, tipo, selector/contenedor/kbps, etiqueta, título, miniatura, peso); a partir de ahí el puente **solo manda ids y claves** (pausar/reanudar/cancelar/borrar) — nada de datos que Python no recibió al encolar.
5. **Progreso**: eventos Python→interfaz monótonos, máximo ~4 por segundo, el porcentaje nunca baja. Los emite Python (`events.emitir`); la interfaz no calcula nada.
6. **Cola** (spec §4): 10 en espera + 1 activa; pausa conserva `.part`; cancelar corta el hilo de verdad y limpia temporales (`.part` solo se conserva en pausa); reintento circular vuelve el ítem a "en espera"; "×" sobre una cancelada la borra.
7. **Pruebas**: los tests unitarios corren sin red (descargador falso + fixtures); las descargas reales se prueban a mano con `tools/probar_descarga.py` (tabla: link → resultado → archivo en disco).
8. **Pausa real** (al implementar B3): pausar corta el hilo igual que cancelar pero SIN borrar `.part` (el hook lanza `Pausada` con los nombres vistos; la cola los guarda y si se cancela desde la pausa, limpia con `downloader.limpiar`). Reanudar vuelve el ítem a "en espera" y yt-dlp reanuda por `.part` (`continuedl`). Un ítem que todavía no arrancó se marca pausa sin arrancar. **Cancelar tiene prioridad sobre pausar.** Pausar un ítem en "procesando" (fase ffmpeg) no se puede: no hace nada.
9. **Cola llena**: al agregar (o reanudar/reintentar) con 10 ya en espera → error nuevo `cola_llena` en `errors.MENSAJES` ("La cola está llena: ya hay 10 descargas esperando...").
10. **Reintento circular** (detalle de 3d.6): automático, **2 reintentos máximo** (el ítem va al final de la espera, por eso "circular") y **solo para códigos transitorios** (`sin_internet`, `tiempo_agotado`, `error_desconocido`, `calidad_no_disponible`, `sin_subtitulos`); los permanentes (`video_privado`, `video_eliminado`, `sitio_no_soportado`, `no_es_video`, `lista_reproduccion`, `restriccion_edad`, `no_disponible_pais`, `link_invalido`) quedan en error de entrada. Agotados los reintentos, queda en error con su mensaje; `reintentar` (a mano) lo devuelve a espera con el contador a cero.
11. **Eventos de la cola Python→interfaz**: solo dos — `cola` (lista completa de ítems: snapshot + id + estado + ruta/error, se emite en cada cambio estructural) y `progreso` {id, fase, porcentaje, descargado, total, velocidad, restante} (máx ~4/s, lo filtra el descargador). Nada más sale del puente (3d.4).
12. **Puente de la cola** (B4): `agregar_descarga(snapshot)` valida en el borde (url_canonica no vacía → si no `link_invalido`; tipo video/musica/imagen y selector presente para video/música → si falta, error nuevo `entrada_invalida`) y devuelve `{id}`; `pausar/reanudar/cancelar/borrar/reintentar_descarga(id)` pasan solo ids de texto (id raro → `false` sin tocar la cola); `cola_actual()` devuelve la lista para la interfaz. Los errores (cola_llena) salen con el contrato `{ok:false, error}` normal.
13. **`imagenes_urls` en el contrato del análisis** (B5): al lado de `imagenes` (data: para mostrar, CSP) viaja la lista PARALELA de URLs reales `imagenes_urls` (solo http(s); misma longitud y mismo filtro que `imagenes`). El snapshot de tipo imagen manda `url_canonica` = la URL real de la foto elegida y `selector` vacío: así el descargador la baja igual que una imagen directa (B2). Sin esto, las fotos de IG/FB/X no se pueden encolar: la UI solo tiene data:.
14. **Insignia de la Cola** (B5): cuenta los ítems ACTIVOS (espera, descargando, procesando, pausa). Terminadas, con error o canceladas no cuentan; el evento `cola` la refresca completo.
15. **Abrir/cambiar carpeta** (B5): `abrir_carpeta(ruta?)` abre en el explorador de Windows (sin ruta usa la de los ajustes; inexistente → `false`); `cambiar_carpeta()` abre el selector de pywebview, guarda el ajuste y devuelve la nueva ruta, o `null` si se canceló. Sin vista propia todavía (llega con Ajustes en Fase 6).
16. **Corte limpio de pausa/cancelar** (B6, fix en vivo): la excepción `Cancelada`/`Pausada` salía de yt-dlp con el traceback completo, y ese traceback mantenía vivos los frames internos (y el `.part` ABIERTO) todo el tiempo del estado pausa. En Windows eso bloquea borrar/renombrar (WinError 32): visto en vivo (un `.part` de 362 MB inborrable y un renombrado fallido de yt-dlp). Fix: al atrapar `Cancelada`/`Pausada` en `downloader.descargar` se limpia `exc.__traceback__` + `gc.collect()` antes de `limpiar`/re-lanzar; el `.part` queda en disco (resumen) pero SIN handle abierto. Tests: `ArchivosBloqueados` en `tests/test_downloader.py` (2 tests que fallaban con el WinError 32 exacto).

## 3e. Fase 4C Parte 0 — cierre de la Fase 4 (16/10/2026, aprobado por Maki)

Plan de la Fase 4C aprobado por Maki (16/10/2026): hacer la Parte 0 y, sin
esperar OK, la Parte B; freno con el REPORTE FINAL.

1. **Nunca sobrescribir (P0.6a)**: dos descargas del mismo título creaban el
   mismo archivo y la segunda pisaba a la primera (pérdida de datos). yt-dlp
   NO deduplica solo: `overwrites=False` (--no-overwrites) **saltea** la
   descarga si el archivo existe (no renombra), y el postprocesador de MP3
   igual pisa el `.mp3` (los temporales bajan a `.webm`/`.m4a`). Solución
   propia: antes de bajar, `validacion.nombre_base_libre(carpeta, titulo)`
   elige un nombre base libre probando "titulo", "titulo (2)", "titulo (3)"…
   y considera **todas las extensiones** (cualquier archivo de la carpeta que
   empiece con "base." cuenta: `.mp4`, `.mkv`, `.mp3`, `.jpg`, `.<idioma>.srt`).
   Ese base se usa tal cual en el `outtmpl` (`base.%(ext)s`), así el archivo
   final no depende del título que traiga yt-dlp; tras el posproceso se
   verifica que el nombre final siga empezando con el base (si yt-dlp lo
   cambia, se avisa por log). Probado con descargas reales repetidas: video
   (`Me at the zoo.mp4` → `(2)` → `(3)`) y música (`mp3` → `(2)`).
2. **Un solo subtítulo .srt (P0.6b)**: se revierte el pedido "es+en" de la
   Parte 0; ahora `downloader._elegir_subs` prefiere el idioma de los ajustes
   y, si no está, usa el otro (es/en); si ninguno existe, no baja nada (sin
   fallar la descarga principal). Manuales tienen prioridad sobre automáticos
   (`writesubtitles` vs `writeautomaticsub`). Un solo `.srt` por descarga.
3. **Nombres de Windows (P0.6c)**: `validacion.sanear_nombre` quita los
   caracteres ilegales (`\ / : * ? " < > |`) y de control, saca el punto o
   espacio final y despega los nombres reservados (`CON`, `NUL`, `COM1`…)
   agregando un guion bajo al primer tramo (`CON` → `CON_`, `CON.txt` →
   `CON_.txt`). `nombre_base_libre` recorta el nombre para que la ruta
   completa (carpeta + nombre + extensión + sufijo) no pase de `MAX_RUTA`
   (240, con margen bajo el límite clásico de 260 de Windows).
4. **Seguridad del borde (P0.7)**: ver el detalle en `PENDIENTES.md` (c) y el
   módulo `miauki/core/validacion.py`. La interfaz no puede colar claves
   (solo las 8 permitidas), ni selectores fuera de un charset acotado, ni
   rutas; "Abrir carpeta"/"Mostrar archivo" solo abren la carpeta de ajustes o
   archivos de la cola; "Cambiar" rechaza rutas peligrosas y verifica escritura.
5. **Tests modificados y por qué**:
   - `tests/test_downloader.py::OpcionesSubs`: reescrito porque `opciones_subs`
     cambió de firma (ahora recibe un idioma + `automatico` + `nombre` y pide
     `subtitleslangs=["<idioma>"]`). Se quitó `test_pide_es_y_en_siempre`
     (esa regla ya no existe) y se agregaron tests de automático y de outtmpl.
   - `tests/test_downloader.py::Descargar` (`test_devuelve_la_ruta…`,
     `test_si_fallan_los_subs…`, `test_sin_subs_activos…`): se agregó
     `"subtitles": {"es": [{}]}` a la info falsa porque la 2ª pasada ahora
     solo ocurre si hay un idioma disponible (antes era incondicional).
   - `tests/test_downloader.py`: constante `AJUSTES.carpeta_descargas`
     cambiada de `C:\Users\prueba\Downloads` a `C:\dl` para que coincida con
     la ruta que devuelve el fake y no choque con la verificación "el archivo
     final está dentro de la carpeta" (P0.7).
   - `tests/test_api.py::test_agregar_descarga…`: ahora espera el snapshot
     normalizado (`kbps=None`), porque el borde completa las claves.
   - `tests/test_validacion.py`: nuevo (P0.7 + P0.6c); reemplaza el viejo
     `nombre_reservado_windows` (que se eliminó de `validacion.py`).
6. **Skills**: security-and-hardening (obligatoria), debugging-and-error-recovery,
   test-driven-development, source-driven-development, incremental-implementation.
7. **Facebook sin IDs de formato (P0.5)**: la descarga de Facebook fallaba de
   forma intermitente ("Requested format is not available") porque los IDs de
   formato (`299+140`) son efímeros y el análisis queda cacheado ~5 min.
   Solución:
   - El análisis ya no devuelve IDs: `analyzer._selector_video(altura, mp4)`
     arma el selector **por altura y códec con respaldos** separados por "/",
     p.ej. `bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/
     bestvideo[width<=1080]+.../best[height<=1080]/best[width<=1080]/best`
     (el filtro por ancho cubre los verticales; `best` es la red final; la vía
     mp4 exige H.264+AAC sin re-codificar). Probado real con el reel/watch de
     Facebook: baja en mkv (AV1+AAC), contenedor real == prometido.
   - `downloader._extraer_con_respaldo`: si yt-dlp falla con
     `calidad_no_disponible`, reanaliza **en silencio** (solo log,
     `analyzer.analizar(url, forzar=True)`) y reintenta UNA vez con un selector
     nuevo de la misma resolución (o la menor disponible); si no hay con qué,
     queda el error. No inventa extracción ni agrega dependencias.
   - El snapshot ahora lleva `resolucion` (allowlist de `validacion` +
     `construirSnapshot` en `js/app.js`) para saber qué altura reanalizar.
   - `errors.py`: `"cannot parse data"` → `requiere_sesion` (Facebook sin
     sesión); el mensaje ya menciona "Ajustes → Cookies".
   - **Tests modificados**: `test_analyzer.py` (aserciones de selector exacto
     `299+140`/`136+140`/`22`/`251+249`/`18`/`270+140` → por altura/códec),
     `test_fixtures.py` (`270+140` → altura/códec), `test_validacion.py`
     (`bestvideo[height<=1080]` pasó de inválido a **válido**: se amplió el
     charset del selector a `[A-Za-z0-9_.,+\-\[\]=<>^/()]`; se agregó
     validación de `resolucion`), `test_api.py` (espera `resolucion=None`),
     `test_errors.py` (caso "Cannot parse data" → `requiere_sesion`),
     `test_downloader.py::ReintentoFormato` (nuevo) y
     `test_tras_cancelar_el_parte…` (más robusto: si `limpiar` ya borró el
     `.part`, no exige que siga; antes el frame del helper mantenía el ydl
     vivo y el archivo quedaba bloqueado hasta el gc).

8. **Cierre de la Parte 0 (P0.10)**: suite **299 tests OK**; a11y en ventana
   real (pywebview + WebView2) **OK** (todos los interactivos con nombre
   accesible); **.exe regenerado** (`dist/Miauki YT.exe`, 85,3 MB) y **smoke
   test OK** (arranca y sigue vivo). P0.8: repo limpio (sin descargas, `.part`,
   `__pycache__`, `.exe` ni binarios trackeados; `.git` ~88,8 MB, casi todo
   PNG de evidencia). P0.9: ver arriba (A8 en PENDIENTES).

## 3f. Fase 5 Parte 0 — cierre de la 4C (17/10/2026, aprobado por Maki)

Plan de la Fase 5 aprobado por Maki (17/10/2026): primero la Parte 0 (preguntas
abiertas + correcciones visuales de la 4C) y después la Parte B (Fase 5 real),
**un commit por porción**, corriendo sin esperar OK intermedio; el freno es solo
con el REPORTE FINAL. Fase 6 no se empieza.

1. **Separador decimal = coma (punto 5)**: en toda la interfaz el decimal va con
   **coma** y el separador de miles con **punto** (uso de Argentina), en **una
   sola función** `formatearNumero(valor, decimales)` de `app.js`; el único
   `toFixed(` del archivo vive ahí dentro (test que lo cuenta). `formatearBytes`
   la usa, y el porcentaje de la barra de progreso también. Valor no numérico o
   no finito → `"—"`.
2. **Scroll de Inicio — causa raíz (punto 8b)**: al entrar la 4C el `h1`
   sr-only quedó como **primer hijo** de `.central`, así que los
   `:nth-child(1/2/3)` con los pisos de las tarjetas se corrían un lugar: la
   tarjeta 3 quedaba **sin piso** y "Más opciones" se cortaba con scroll. Se
   cambió a **`:nth-of-type`** (cuenta solo `<section>`). Además la fila de
   calidad **envolvía** por el botón "Más opciones" (necesitaba 760 px y había
   743): relleno lateral del segmentado 16→12 px. Medición final (`p5_medir.py`
   sobre `.central`): **0 px en 1200×720, 1355×721 y 1600×900** en los 4 estados
   de Inicio (vacío, resultado, aviso, aviso+resultado). A la **ventana mínima
   (880×560)** queda un scroll interno de ~147 px: límite conocido del diseño a
   esa ventana chica (documentado en `PENDIENTES.md`).
3. **El aviso de la cola no mueve la tarjeta 1 (punto 8c)**: el aviso
   "Agregada a la cola" **reemplaza** a la ayuda tenue del paso 1 (en vez de
   sumarse debajo) y los dos comparten **altura reservada de 25 px**; así
   aparecer/desaparecer no cambia el alto de la tarjeta. Ojo: `.ayuda-tenue` es
   `display:flex`, así que necesita su propia regla `[hidden] { display:none }`
   (el `[hidden]` del navegador pierde ante `display:flex`; mismo caso que
   `.aviso-cola`/`.cola-vacia`).
4. **El `h1` de pantalla no dibuja anillo (punto 8a)**: recibe foco por programa
   (para que el lector anuncie la sección) con `.pantalla-titulo:focus {
   outline: none }`, sin `:focus-visible`. El anillo se mantiene para teclado en
   los controles reales (nav, botones, campo, interruptores).
5. **Tooltip propio en vez del `title` del sistema (punto 8d)**: el tooltip
   nativo de Windows **no aparece al navegar con teclado**, así que los botones
   de **solo ícono** (acciones de la Cola) y los de "Guardar en" usan un globo
   propio (`iniciarTooltips` → `div.globo` con `position: fixed`, `z-index`
   alto) que se muestra con **hover y con foco** y no lo recorta el `overflow`
   de la lista de la Cola. Es solo visual (`aria-hidden`): el nombre accesible
   sigue en el `aria-label` de cada botón. Verificado en vivo: visible con foco
   y con hover, oculto al salir, siempre dentro de la ventana.
6. **El foco sobrevive a la Cola (punto 3)**: verificado en vivo que 20 eventos
   de progreso **actualizan en el lugar** (mismo nodo, 0,4 ms, sin repintar) y
   que el foco puesto en "Pausar" **no se mueve**. Como un **repintado** por
   cambio de estado sí borra los botones, `pintarCola` ahora recuerda qué botón
   tenía el foco (id del ítem + acción) y se lo **devuelve al botón
   equivalente**; si ese botón ya no existe (el ítem cambió de estado), cae a
   `body` sin errores.
7. **Subtítulos (punto 1d) — confirmado sin cambios de código**: con un video
   **sin** subtítulos el interruptor queda **deshabilitado y desmarcado**
   (`data-subs="no"`) y **no se pisa** la preferencia guardada del usuario; al
   analizar un video **con** subtítulos se **restaura** el valor del usuario (no
   el predeterminado); si el usuario lo apaga, el guardado va al puente y se
   respeta. Verificado con la ventana real + `ajustes.json` (respaldo y
   restauración del archivo real durante la prueba).
8. **"Mostrar archivo" / "Abrir carpeta" protegidos (punto 4) — confirmado**:
   con la **`Api` real** (sin dobles) se probaron 12 rutas ajenas
   (`C:\Windows\System32\calc.exe`, `C:\`, `C:\Program Files`, `..\..\afuera`,
   vacío, `None`, un número…): todas **rechazadas** (`data:false` o error
   amable) y **nada se abrió**. Ya estaba cubierto por los tests de `P0.7`.
9. **Decisiones cerradas por Maki (17/10/2026)**:
   - La **confirmación al cerrar con descargas en curso** con diálogo nativo
     OK/Cancel está bien así (es lo que ya hace `app.py`).
   - La barra de progreso al **100 % en "procesando"** está bien, respetando
     `prefers-reduced-motion` y `.reducir-efectos`.
   - La **reducción del `.git`** (~88,8 MB, casi todo PNG de evidencia) **NO se
     hace ahora**: queda para la entrega final, con copia de respaldo previa,
     porque cambia los códigos de commit citados en la documentación.

## 3g. Fase 5 Parte 0 (cierre) y Parte B - implementación (20/10/2026)

### 1(a) — "la app se cierra sola": dos corridas largas y un bug propio encontrado

- **Qué se hizo**: dos corridas de 35 min con la misma pila que usa la app
  (`pywebview` + `Api` real + cola real), con ciclos de uso real: navegar las 5
  pantallas, scroll y tooltip, redimensionar a 1200×720 / 880×560 / 1600×900 /
  1355×721, analizar 3 links rotando (dos de YouTube y la foto de X), encolar,
  pausar, reanudar, cancelar y borrar.
- **Instrumentación** (script de prueba, fuera del repo:
  `C:\Users\Maki\AppData\Local\Temp\opencode\p5_soak.py`):
  `faulthandler` a archivo propio (`faults-*.log`), `sys.excepthook` y
  `threading.excepthook`, `atexit` ("SALIDA LIMPIA"), **código de salida** en
  `resultado.txt`, latido cada 5 s, colector de errores JS, manejadores
  `closing`/`closed` de pywebview, Crashpad de WebView2 y Visor de eventos.
- **Corrida 1 (02:44–03:16)**: 84 ciclos, **1092 operaciones OK, 0 fallos**,
  `faults.log` de **0 bytes**, `errores js []` en los 84 muestreos. **La ventana
  se cerró sola a los 32 minutos** de 35 y el proceso salió con código 0.
- **Corrida 2 (03:27–04:03)**: 93 ciclos, **35 minutos completos**
  (`FIN DEL SOAK`), `EVENTO closing` → `EVENTO closed` (los disparó el propio
  script al cerrar), `SALIDA LIMPIA (atexit ejecutado)`, código de salida 0,
  `errores js []` siempre. **No se cerró sola.**
- **Lo que sí apareció en la corrida 2**: **9 violaciones de acceso**
  (`Windows fatal exception: access violation`) con la pila
  `ctypes.wstring_at` ← `clipboard._texto_windows` ← `link_del_portapapeles`.
  Era un **bug de B1**: `wstring_at(puntero, 64 K)` lee *exactamente* 64 K
  caracteres y **no se detiene en el NUL**, así que sobre un bloque de 40 bytes
  se salía de la memoria. **Arreglado**: se pide `GlobalSize` y se lee solo lo
  que entra en el bloque real. Verificado con **600 lecturas** (texto corto,
  texto de 2000 caracteres y sin link) y **0 volcados**, más 2 tests nuevos que
  fijan la lectura acotada.
- **Antes ese mismo día** (evidencia previa): dos dumps de renderer de WebView2,
  ambos `0xC0000005 ACCESS_VIOLATION` en la **misma** dirección
  `msedge.dll+0x53F2555`, con el runtime **153.0.4234.48** mientras Edge estable
  va **154.0.4258.37**. El Visor de eventos no registra nada: los cierres de
  renderer de WebView2 no aparecen como "Application Error".
- **Conclusión honesta**: el síntoma existe (**1 de 2 corridas lo reprodujo**) y
  el cierre no deja rastro: ni excepción de Python, ni evento de Windows, ni
  dump nuevo, ni `closing`. La causa sigue sin nombrarse. Lo que sí se encontró
  y se cerró es un AV propio en el portapapeles, que en otra máquina podría
  matar el proceso y verse exactamente como "la app se cerró sola".
- **Decisión**: el código queda arreglado y probado. Para el cierre definitivo
  queda **actualizar el runtime de WebView2** (Evergreen oficial) y repetir la
  corrida larga; si vuelve a pasar, capturar con `--remote-debugging-port` +
  `edge://inspect`. No se hace sin el OK de Maki porque cambia su máquina.

### 1(b) — Facebook: la v2.6 no tenía lógica propia; yt-dlp tampoco soporta fotos

- **Código leído de la v2.6** (`...\Miauki YT MiMo 2.6 v2.6 OpenCode\src\core\`):
  `engine.py` (probe → yt-dlp, sin ninguna rama de Facebook), `direct.py`,
  `utils.py` (solo saca el nombre del sitio). **No existía** código de
  Facebook: no hay descarga de foto, ni `og:image`, ni `fbcdn`.
- **Qué se ejecutó**: `core.engine.probe()` aislado sobre 7 links reales.
  - `photo.php?fbid=...` → `Unsupported URL`
  - `/photo/?fbid=...` → `Unsupported URL`
  - `share/p/...` → `Unsupported URL`
  - álbum `media/set` → `Unsupported URL`
  - `/photos/a.111/222/` → unsupported
  - `/posts/pfbid...` → extractor `facebook` **engancha** ("Cannot parse data")
  - CONTROL `/watch/?v=` → extractor `facebook` engancha ("Cannot parse data")
- **Por qué**: en `yt_dlp` 2026.08.19 el `_VALID_URL` de `FacebookIE` solo
  acepta `photo.php` con `?v|video_id|story_fbid=` (video), y **no tiene
  ninguna ruta de fotos**. No es un bug de Miauki v1.0: es una limitación
  del motor.
- **Cómo queda en la v1.0**: `images._via_facebook` existe pero usa
  `FacebookIE`, así que un link de foto devuelve "Ese sitio todavía no lo
  soportamos"; el analizador sí da el mensaje específico ("Las fotos de
  Facebook todavía no se pueden analizar"). Ya estaba en `PENDIENTES`
  (investigación 0.2, 16/10) pero **nunca se había reportado**. Propuesta
  nueva (sin implementar) en `PENDIENTES.md`.

### Punto 2 — pruebas reales del motor (con lo que ya había)

| Prueba | Resultado exacto |
|---|---|
| Foto de X (`.../status/2110183275461513256/photo/1`) | JPEG **2992×1640**, **224.183 B**, `pbs.twimg.com/media/HUjf8tjXQAEOlBY.jpg?name=4096x4096` |
| Miniatura de YouTube al máximo | `RpOlTN2xdwg` → `maxresdefault.jpg` **1280×720** (29.123 B); `jNQXAC9IVRw` solo tiene `hqdefault` **480×360** (20.969 B) porque ese video no tiene `maxres` |
| Música 320 kbps (video de la Fase 3B) | **762.284 B** reales vs **760.000** estimados (**+0,3 %**) |
| Música 128 kbps | **304.940 B** reales vs **304.000** estimados (**+0,3 %**) |
| Título con comillas, barras, emoji y largo | 532 caracteres → saneado a **183**, sin caracteres ilegales, ruta de **232** caracteres (< 260), descarga 240p OK |

TikTok real y YouTube 4K/8K **no se prueban acá**: quedan como "pruebas del
motor (Fase 8)" porque hacen falta links que consigue Maki.

### Parte B (B1–B6)

- **B1** `core/clipboard.py` real (Win32 por `ctypes`, CF_UNICODETEXT, sin
  dependencias, nunca loguea el contenido, tope 2048) + `Api.link_portapapeles`
  + 9 tests. Verificado en vivo.
- **B2** barra "Wow... un link: ¿Lo usamos?" conectada al portapapeles real:
  aparece al abrir y al volver a la ventana (debounce 1500 ms), "Usar" lo
  copia al campo y cierra, "Pegar" lo trae, el link descartado no se repite.
- **B3** Ajustes escribe de verdad (`obtener_ajustes`/`cambiar_ajuste`):
  carpeta + "Cambiar carpeta", idioma de subtítulos, incluir subtítulos,
  cookies del navegador, fxtwitter e idioma de la interfaz, con aviso
  "Guardado." Verificado contra el archivo real.
- **B4** Acerca de lee `app_info` por el puente (nombre, versión, autor, año,
  lema) y muestra la atribución de ffmpeg (GPLv3).
- **B5** "Peso total descargado": al terminar la descarga muestra el **peso
  real** (archivo + subtítulos hermanos). Antes de descargar queda "—".
  Verificado: 985 KB estimados → **727 KB** reales en pantalla.
- **B6** verificación: capturas a 1600×900, 1355×721, 1200×720 (vacío y con
  resultado real) y 880×560; `.exe` recompilado; teclado real (orden de Tab y
  anillo de foco); contraste AA medido sobre píxeles; tokens en vivo.
- **Hallazgo del soak, corregido**: "Quitar" de la Cola ofrecía borrar
  terminadas y con error pero `Cola.borrar` solo aceptaba `cancelada`, y el
  botón "Limpiar" **no tenía manejador ni método**. Ahora `borrar` acepta
  `terminada`/`error`/`cancelada` (nunca un ítem activo) y `limpiar()` saca
  las terminadas y canceladas, con `Api.limpiar_descargas` y 3 tests nuevos.



## 3h. Fase 5C + Fase 6 - decisiones de Maki (20/10/2026, aprobado por Maki)

Maki aprobó la Fase 5 y fijó estas 9 decisiones antes de la tanda:

1. **WebView2**: actualizar el runtime Evergreen de esta PC a la línea 154 con el
   instalador oficial de Microsoft (firma Authenticode verificada) y repetir la
   prueba larga.
2. **LICENCIAS.txt**: sí, es obligatorio porque el programa se va a vender.
3. **Fotos de Facebook**: no entran en la v1.0; queda el mensaje amable actual y
   la propuesta en `PENDIENTES.md`.
4. **Barra del portapapeles**: FLOTANTE (no empuja el contenido).
5. **Listas de reproducción**: no entran en la v1.0; se mantiene el mensaje
   "no soportada".
6. **"La app se cierra sola"**: Maki nunca lo vio usándola. El cierre del soak
   puede haber sido del arnés de prueba o del bug de memoria del portapapeles ya
   corregido.
7. El punto 1(c) que faltaba era el scroll de 23 px: ya cerrado en `9c958c1`.
8. **Pruebas del motor**: YouTube 4K de 1 minuto
   `https://www.youtube.com/watch?v=x91MPoITQ3I`. El link real de TikTok no
   llegó (Maki mandó la portada): queda pendiente para la Fase 8.
9. **Modelo comercial**: demo gratuita limitada y pago único (5 a 8 dólares) con
   licencia para UNA persona/PC. Esta tanda solo diseña los informes; no se
   escribe código de licencias.

Consecuencias que se aplican en esta tanda:

- El Historial lleva **tope de 500 entradas** (reemplaza la auto-limpieza a 30
  días de la spec §4: la decisión nueva manda).
- Se quita el selector de idioma de Ajustes (un solo idioma); la clave
  `idioma_interfaz` sigue en `settings.py`.
- La barra flotante no puede tapar controles interactivos ni sumar scroll.
- Los procesos de WebView2 se atan a Miauki con un **Job Object de Windows**
  (`KILL_ON_JOB_CLOSE`), nunca por nombre de proceso: así Edge, Teams u Outlook
  no se ven afectados.
- El perfil de WebView2 deja de ser una carpeta temporal anónima
  (`%TEMP%\tmpXXXX\EBWebView`) y pasa a una ruta propia y estable dentro de la
  carpeta de datos de Miauki.

## 3i. Fase 5C - cierre técnico de la Fase 5 (20/10/2026)

Resultados de la tanda (los detalles de cada punto están en el reporte final):

- **A1 – WebView2 y cierre**: WebView2 se actualizó con el bootstrapper oficial
  (firma Authenticode verificada, exit 0): **153.0.4234.48 → 155.0.4283.62** (instaló
  la última estable, no la 154; Edge quedó en 154.0.4258.37). El cierre de la app
  quedó instrumentado (`closing`, `closed`, vuelta de `webview.start`, código de
  salida, `atexit`) y **se encontró un bug propio**: enganchar `ProcessFailed` de
  `CoreWebView2` desde el evento `loaded` **congelaba la interfaz** (la ventana no
  cerraba ni con WM_CLOSE). Se sacó el enganche; hoy la app cierra con código 0 y el
  log muestra `closing → closed → webview.start volvió → código 0`. `ProcessFailed`
  queda pendiente para Fase 8 (vía que no bloquee el hilo de la UI).
- **A2 – procesos**: Job Object con `KILL_ON_JOB_CLOSE` + perfil propio
  (`dir_datos()/webview2`) en vez de matar procesos por nombre. Un Edge ajeno no se
  ve afectado (test real).
- **A1 – soaks finales (2 × 35 min, código final `994ef5b` limpio)**: los dos
  completos, **93 ciclos cada uno, 0 fallos**, con uso real automatizado (analizar
  YouTube y X, encolar, pausar, reanudar, cancelar, borrar, cambiar de pantalla,
  redimensionar a los 4 tamaños, revisar errores de JS vacíos). Los dos cerraron
  desde el evento `closing` → `closed` → vuelta de `webview.start` → **código 0** →
  atexit. **El cierre solo NO se reprodujo** después de actualizar WebView2 y sacar
  el enganche de `ProcessFailed`: 0 veces en 2 corridas, contra 1 vez (a los 32 min)
  antes del cambio. Se deja la instrumentación puesta para Fase 8.
- **A3 – barra del portapapeles FLOTANTE**: `position: fixed` arriba a la derecha,
  `--z-barra: 5`, `role="status"`, se descarta con Escape o con la ×. Medido en
  ventana real en 1600×900, 1355×721, 1200×720 y 880×560, en las 5 pantallas:
  **0 controles tapados** (campo del link, botones, selector de calidad y MIAUK!),
  scroll del documento 0 y el scroll interno de Inicio queda **igual con y sin
  barra**. A 880×560 la barra tapa parte del banner (decorativo, no controles):
  límite conocido; el reemplazo por el texto de ayuda queda para Fase 8.
- **A4 – Acerca**: gracias, autor, año, Instagram, "Abrir carpeta de registros",
  "Copiar información de diagnóstico" (sin rutas personales, cookies, links ni
  títulos), "Detalles técnicos" plegable, aviso legal spec-lock y "Licencias de
  terceros" por lista blanca (`abrir_enlace("licencias")`).
- **A5 – LICENCIAS.txt**: 86 KB con GPLv3 completa, oferta escrita de código fuente
  de FFmpeg 9.0.2 (link al tarball exacto verificado, oferta por 3 años), OFL de
  Fredoka y Caveat, BSD, MIT, PSF, Unlicense, Simple Icons CC0 y la aclaración de
  PyInstaller. `tools/generar_licencias.py` lo regenera, el build **falla si falta**,
  lo embebe y lo copia al lado del `.exe`. Nada bloquea la venta por licencias.
- **A6 – Ajustes**: se sacó el selector de idioma de la interfaz (la clave
  `idioma_interfaz` sigue en `settings.py`); entró el interruptor "Guardar
  historial" (activado por defecto) con su línea de explicación.
- **B1/B3 – datos**: `historial.json` atómico, tope 500 (reemplaza la limpieza a 30
  días de la spec), tolerante a corrupción y sin guardar nada con el interruptor
  apagado; `cola.json` aparte que recupera las descargas sin terminar como
  "Interrumpida" y **nunca reanuda solo**.
- **A7 – 4K**: `x91MPoITQ3I` ("SAMSUNG 4K DEMO QLED", 69 s) analizado y descargado.
  Formatos hasta **2160p** (AV1/VP9/VP9.2, 37 formatos de video; alturas
  2160/1440/1080/720/480/360/240/144). "Mejor" elige **2160p AV1 + Opus → MKV**
  (descarga real: 127,2 MB, 3840×2160 60 fps, AV1 + Opus); "Equilibrada" 1080p
  AVC/AAC → MP4; "Liviana" 480p → MP4. El aviso de runtime JS aparece pero **con y
  sin `node` el resultado es idéntico** (37 formatos, mismas alturas y códecs): hoy
  no recorta nada en este video. Descarga de prueba borrada.
- **B4 – pruebas**: **408 tests OK** (sin internet). Cierre forzado medido de verdad:
  proceso descargando → `taskkill /F /T` → `cola.json` quedó con el ítem
  `"descargando"` → al arrancar de nuevo, `cargar_pendientes() = 1`, estado
  **"interrumpida"**, sin archivos nuevos ni parciales. `.exe` regenerado con el
  código final (85,4 MB): `LICENCIAS.txt` al lado **y** embebido (86.390 B en el
  paquete), `--version` = 1.0.0 y `--selftest` con los 6 chequeos en OK.

## 3j. Fase 7 - decisiones de Maki (20/10/2026, aprobado por Maki)

1. **yt-dlp se actualiza solo**: comprobación automática en cada inicio **y** un
   botón manual en Ajustes, de color **rosa fucsia neón**.
2. **Mejoras rápidas aprobadas**: (a) modo/aviso de compatibilidad para MKV/AV1;
   (b) arrastrar y soltar un link sobre la ventana **y** Ctrl+V que pegue y analice;
   (c) parpadeo en la barra de tareas al terminar una descarga; (d) recorrido guiado
   "Así de fácil se usa" en vez de una pantalla de bienvenida.
3. **La versión en inglés va al final del proyecto**: todo texto nuevo va en
   `js/strings.es.js` con identificador claro, nada hardcodeado.
4. **Prueba en Windows 10 limpio**: se deja lista y guiada cuando el `.exe` esté
   (Parte E). Maki todavía no abrió el `.exe`.
5. **Link de TikTok de prueba**:
   `https://www.tiktok.com/@missho3kage/video/7698542142985227551`.
6. **Demo y licencia: no se implementan ahora** (Maki primero quiere entender cómo
   funcionan). **Logos de las plataformas**: Maki consulta a un profesional; el
   banner no se toca.



## 3k. Fase 7 - Parte 0: datos de prueba, sitio e historial (20/10/2026)

**0.1 Carpeta de datos.** `miauki/paths.py` respeta `MIAUKI_DATOS` (ruta
absoluta) antes que `portable.flag` y que `%LOCALAPPDATA%`. Cada `test_*.py`
importa `tests/apoyo.py` (carpeta temporal por corrida) y `test_zz_datos_reales`
falla si algo tocó la carpeta real; `tools/_entorno.py` hace lo mismo en las
herramientas. Antes/después de la limpieza: historial **188 -> 0** entradas,
cola **0 -> 0**, `ajustes.json` intacto (222 B). Copia de seguridad en
`%TEMP%\miauki-backup-20261020-191031\` (historial, cola y ajustes).

**0.2 Sitio "otro".** Era un bug: la interfaz nunca mandaba `sitio` y el borde
lo ponía en "otro". Ahora el sitio se deduce del link en
`validacion.snapshot_limpio` (`sites.sitio_de_url`), no se le cree a la
interfaz. Verificado con una descarga real de YouTube: la entrada nueva quedó
`sitio: youtube`.

**0.3 TikTok real** (`@missho3kage/7698542142985227551`). Título "gnnn 😁",
autor missho3kage, **10 s**, sin miniatura, tipos video/música/imagen, sin
subtítulos. Formatos que ofrece el sitio: 9 entradas (576x1024 H.265 598 kbps;
720x1280 H.264 901 kbps; 720x1280 H.265 703 kbps; 1080x1920 H.265 1329 kbps;
más el audio MP3), **todos progresivos** (video+audio juntos, mp4).
- Calidades de la app: **1080p (Mejor)**, **720p (Equilibrada)** y 576p extra.
- Descarga real: Mejor **1,68 MB** en 1,7 s (estimado 1,68 MB), Equilibrada
  **0,89 MB** (estimado 1,14 MB, aprox), Liviana **0,76 MB** (estimado 0,76 MB).
  Contenedor real **mp4** en los tres casos. No hizo falta cookies.
- **Fallo real encontrado y corregido**: con el User-Agent de yt-dlp el sitio
  respondía `Unexpected response from webpage request`; yt-dlp avisa que intenta
  impersonación y no tiene objetivo disponible. Con un User-Agent de navegador
  real (Chrome 140) funciona. Se aplica **solo a TikTok**
  (`analyzer.UA_NAVEGADOR`), sin agregar `curl_cffi` (dependencia nueva con
  binarios).
- **Dos bugs de formato, medidos y corregidos**: (a) el selector filtraba
  primero por alto, así que en un video vertical "1080p" bajaba **576p**
  (ahora el filtro por ancho va primero); (b) un formato progresivo se
  anunciaba como MKV aunque el archivo salía mp4 (ahora el contenedor es el
  `ext` real del formato elegido).

## 3l. Fase 7 - Parte A: actualizador y tarjeta del motor (20/10/2026)

**Diseño.** `docs/ACTUALIZADOR.md`: fuente **PyPI** (wheel `py3-none-any` +
`digests.sha256` del JSON oficial) y cruce con el lanzamiento de GitHub; sin
firma GPG (pediría GnuPG o una dependencia nueva); tope 20 MB; extracción con
protección zip-slip; nunca `.exe`; nunca baja de versión; una versión que no
pasa la prueba de humo queda marcada y no se reintenta.

**Actualización real probada.** Partiendo de un motor "viejo" simulado
(2026.08.01 en `MIAUKI_DATOS`), el actualizador bajó **2026.8.19** de PyPI,
verificó el sha256, cruzó la etiqueta de GitHub, corrió `--probar-motor` en un
proceso aparte y la activó (`motor.json`: `activa 2026.8.19`, `anterior
2026.08.01`). Con esa versión descargada, YouTube y TikTok analizan y descargan
igual que antes. **PyPI no tiene hoy ninguna versión más nueva que la incluida**
(2026.08.19): el botón responde "Ya tenés la última versión".

**Botón rosa neón.** Token `--rosa-neon` (`#ff2f95`) con resplandor, usado
**solo** en "Buscar actualización" (y en el "Actualizar motor" del error, mismo
componente). Texto `--tinta-sobre-neon` (`#170410`). Contraste medido sobre
píxeles reales de las capturas (fondo más repetido de la zona del botón y el
píxel más oscuro del texto, fórmula WCAG):

| Estado | Fondo medido | Contraste |
|---|---|---|
| Normal | `#ff2f95` | **5,74:1** |
| Hover | `#ff6ab4` | **7,51:1** |
| Presionado | `#e8347f` | **4,93:1** |

**Estados y mensajes.** Normal, hover, presionado, foco con teclado (anillo
blanco de 3 px) y ocupado (`aria-busy` + `aria-disabled`, sin `disabled`: así
conserva el foco y el contraste). Los textos están en `strings.es.js`
(`motor.*`): "Buscando…", "Ya tenés la última versión.", "Actualizado a
<versión>. Se usa desde que reiniciés Miauki." / "…Ya se está usando." y "No se
pudo comprobar (¿tenés internet?)". La tarjeta muestra versión, si es *incluida*
o *actualizada* y la última comprobación como `dd/mm/aaaa HH:MM`.

**Aviso y error.** Cuando la comprobación del inicio actualiza, se muestra
"Motor actualizado" con el aviso flotante existente (sin robar el foco, se va
solo). El error real de motor viejo (`motor_viejo`, mensajes de yt-dlp
capturados) muestra el botón "Actualizar motor" debajo del error del análisis en
Inicio y dentro de la fila fallida de la Cola.

**Pruebas con el `.exe` (A4).** Con `MIAUKI_DATOS` aparte, arrancando desde un
motor 2026.08.01: bajó 2026.8.19, la probó con `Miauki YT.exe --probar-motor`
(proceso aparte, código 0) y la activó (`activa 2026.8.19`, `anterior
2026.08.01`). Sin internet (proxy inválido): abrió en **2 s**, siguió con el
motor incluido y no mostró ningún aviso (`URLError` solo en el registro).
Con el interruptor apagado: no comprobó nada (no creó `motor.json` ni escribió
una línea del actualizador). Paquete corrupto y falla de importación con
reversa: cubiertos por `tests/test_actualizador.py` (sha256 que no coincide,
zip-slip, prueba de humo que falla y vuelve al motor anterior).

**Espacio.** Ajustes ya tenía scroll en 880x560 antes de esta tarjeta (535 > 363
medido): la tarjeta no cambia esa condición. En 1600x900 no hay scroll
(642 = 642).

## 3m. Fase 7 - Parte B1: "Máxima compatibilidad" (20/10/2026)

Interruptor en Ajustes, **encendido por defecto** (`maxima_compatibilidad` en
`settings.py`), con el texto de Maki: "Máxima compatibilidad" y "Videos que se
abren en cualquier reproductor (hasta 1080p). Desactivalo para bajar en 4K/8K."

Encendido, `analyzer` ofrece **solo H.264 + AAC en MP4 hasta 1080p**: filtra los
videos a `avc1`, el audio a `mp4a`, y recorta las alturas a 1080 (el lado corto,
así un vertical 1080x1920 sigue siendo 1080p). "Más opciones" no muestra nada
por encima. Si el sitio no ofrece H.264 en ningún lado se sigue con lo que haya
—mejor algo descargable que una lista vacía— y si solo hay resoluciones más
grandes baja a la más chica existente. Apagado, vuelve a ofrecer todo (4K/8K).

Con el link real `https://www.youtube.com/watch?v=x91MPoITQ3I` (SAMSUNG 4K DEMO,
1:09):

| Ajuste | Opciones que ofrece |
|---|---|
| Encendido | **Mejor · 1080p** (mp4/h264), Equilibrada · 720p, Liviana · 480p |
| Apagado | **Mejor · 2160p** (mkv/vp9), 1440p, Equilibrada · 1080p, 720p, Liviana · 480p |

Las etiquetas coinciden con la realidad: el "Mejor" dice 1080p solo cuando lo
que baja es 1080p. Cada opción ahora lleva `codec` (`h264`, `hevc`, `av1`,
`vp9`); si el formato elegido es MKV, AV1 o VP9 aparece la línea chica: "Este
formato puede no abrirse en el reproductor de Windows. Probá con VLC." (texto
fijo, en `test_textos`). La caché de análisis incluye el ajuste: cambiarlo
obliga a volver a analizar.

## 3n. Fase 7 - Parte B2: Ctrl+V y arrastrar y soltar (20/10/2026)

**Ctrl+V.** Si el foco **no** está en un campo de texto, la app lee el
portapapeles por el puente de Python (`clipboard.py`, ctypes,
`CF_UNICODETEXT`), saca el primer link con `link_en_texto` y lo valida con
`sites` en el borde (`api.pegar_link`): pone el link en el campo y **analiza**.
Con el foco **en** el campo manda el pegado normal del navegador y, después de
pegar, el campo valida y analiza si es un link. El texto del portapapeles no se
registra en ningún lado (misma regla que la barra de la Fase 5) y solo se lee
ante un Ctrl+V explícito.

**Arrastrar y soltar.** En cualquier pantalla: `dragover` y `drop` se cancelan
a nivel documento (el navegador no abre el archivo ni navega al link), aparece
una capa de vidrio con "Soltá el link acá" (`pointer-events: none`: no atrapa
el foco ni tapa el arrastre), y al soltar: si hay archivos se ignora el archivo
y se avisa "Eso es un archivo. Soltá el link de un video."; si el texto no
trae un link de un sitio que sepamos bajar, "Eso no parece un link. Probá con
uno de YouTube, TikTok, X, Instagram o Facebook."; si trae un link, va a
Inicio, lo pone en el campo y analiza. Los mensajes se anuncian por la región
viva que ya existía (`#paso1-error`, `role="alert"`).

**Probado en ventana real** (no solo tests): con el portapapeles real,
Ctrl+V sin foco en el campo analizó "Me at the zoo" (jNQXAC9IVRw); con foco en
el campo, Ctrl+V pegó y analizó; un `dragenter` mostró la capa; soltar un link,
un texto, un archivo (`.mp4`), una imagen (`.jpg`) y un archivo junto con un
link dio el resultado esperado en los cinco casos, y `drop`/`dragover`
quedaron cancelados (`defaultPrevented: true`).

**Textos nuevos** (para aprobación de Maki, en `strings.es.js`): "Soltá el link
acá", "Eso es un archivo. Soltá el link de un video.", "Eso no parece un link.
Probá con uno de YouTube, TikTok, X, Instagram o Facebook." y "En el
portapapeles no hay un link que podamos bajar."

## 3o. Fase 7 - Parte B3: aviso al terminar una descarga (20/10/2026)

Cuando una descarga **termina bien** (no error ni cancelada) y la ventana **no
está en primer plano**, se hace parpadear el botón de la barra de tareas y el
borde de la ventana **hasta que la persona vuelve**. Si la ventana ya está al
frente no se hace nada, y nunca hay sonido.

Se usa `FlashWindowEx` (user32, ctypes) con `FLASHW_ALL | FLASHW_TIMERNOFG`,
que según la documentación de Microsoft (`FLASHWINFO`) "sigue parpadeando hasta
que la ventana pase a primer plano". `esta_al_frente` compara
`GetAncestor(GetForegroundWindow(), GA_ROOT)` con el `hwnd`, y además trata la
ventana minimizada como "no al frente" (`IsIconic`: Windows a veces la deja como
"activa"). El `hwnd` se busca por proceso y título
(`hwnd_propio("Miauki YT")`): nunca se confunde con otra ventana igual de otro
programa y no hace falta que pywebview exponga su handle.

La decisión vive en `core/ventana.py` (`AvisosDeFin`), separada de Windows con
`destello` y `al_frente` inyectables, y se engancha al evento `cola` que la cola
ya emitía (`events.suscribir`, nuevo). No avisa dos veces por el mismo ítem ni
de lo que ya estaba terminado al abrir la app, y dos descargas que terminan
juntas dan un solo destello.

**Probado en ventana real** disparando por el mismo camino que usa la app
(`events.emitir("cola", ...)`): al frente → no pide destello; minimizada →
`esta_al_frente` False y `FlashWindowEx` aceptado (True); visible pero sin foco
(clic en el escritorio) → también; un ítem en error → no avisa; el mismo ítem
repetido → no avisa de nuevo. Tests de la decisión en `tests/test_ventana.py`.

## 3p. Fase 7 - Parte C: recorrido guiado "Así de fácil se usa" (20/10/2026)

No es una pantalla de bienvenida: son **7 pasos** que señalan cosas reales de la
app, una sola vez (`recorrido_visto` interno en ajustes) y repetible desde
Acerca → "Ver el recorrido". Si un paso apunta a algo que no se ve (por ejemplo
la columna "Guardar en" en ventana angosta, que se esconde bajo 1000 px), ese
paso **se saltea** y el contador se recalcula ("1 de 6").

- Diálogo `role="dialog" aria-modal="true"` con `aria-labelledby`/
  `aria-describedby`, foco atrapado **solo mientras está abierto**, Escape
  cierra, botones "Anterior"/"Siguiente"/"Entendido"/"Saltar" y contador
  "3 de 7". Al cerrar, el foco vuelve al botón que lo abrió.
- Resaltado con un anillo (`box-shadow` hacia afuera con los tokens
  `--rosa-neon` y `--z-recorrido*`): el elemento señalado **nunca queda tapado**.
  El cartel busca lugar alrededor (abajo, arriba, derecha, izquierda) y, si el
  elemento es enorme, resalta su franja superior para que el cartel entre sin
  taparlo. En la barra lateral el cartel va a la derecha (abajo taparía el menú).
- Se mide el estilo real (`getComputedStyle`) y no el atributo `hidden`, porque
  los botones del menú llevan `hidden` pero el CSS los muestra igual.
- Se muestra al abrir, con 500 ms de aire para que la página se asiente, y se
  marca como visto al mostrarlo (si se cierra la app en el medio no reaparece).
  Mientras el recorrido está abierto, Ctrl+V y el arrastrar quedan en pausa.
- Textos nuevos en `js/strings.es.js` (`recorrido.*`), **pendientes de
  aprobación de Maki**.

**Probado en ventana real**: primera vez (7 de 7, foco en "Siguiente", el cartel
no tapa el objetivo en ningún paso, termina con "Entendido" y guarda
`recorrido_visto`), repetir desde Acerca y cerrar con Escape del teclado
(devolviendo el foco al botón), ventana de 880×560 (6 pasos: saltea "Guardar
en"), y "Saltar". Capturas de los 7 pasos a 1600×900 y de 3 pasos a 880×560 en
`%TEMP%\opencode\capturas\f7c\` (fuera del repo). Contrato en
`tests/test_recorrido.py` (9 tests).

**Para las herramientas de captura**: sus carpetas de datos son nuevas, así que
escriben `recorrido_visto: true` antes de abrir la ventana para que el recorrido
no tape las escenas.

## 3q. Fase 7 - Parte D: detalles de interfaz (20/10/2026)

Siete arreglos chicos, un commit cada uno (D3 y D4 comparten `85d4afb`: los
íconos de tipo son los mismos tres SVG para Historial y Cola).

- **D1 - relleno y títulos.** Cola, Ajustes y Acerca no tenían el relleno de
  Historial: el título de pantalla arrancaba pegado al borde izquierdo de la
  tarjeta. Ahora las cuatro usan `var(--esp-3) var(--esp-6)`. Los lemas
  manuscritos girados (columna derecha y pie de la barra lateral) suman 4 px a
  los costados para que la inclinación no toque el borde.
- **D2 - Acerca.** Los cinco botones pasan de 8 a 12 px de aire y de 4 a 12 px
  de margen arriba. La versión muestra `v1.0.0 · 2026` y se saca "Año 2026" de
  la línea del autor (la clave `acerca.anio` se eliminó).
- **D3 - Historial.** Ícono por tipo (video/música/imagen) y por sitio (marca
  real o globo) siempre con el texto al lado; el sitio "otro" **nunca** se
  muestra: se usa el dominio del link (`ejemplo.com`) o "Sitio web" si no se
  puede leer. Barra de scroll fina (8 px) en la lista.
- **D4 - Cola.** Ícono y color por estado, medidos sobre el pixel real de la
  fila (peor caso `rgb(32,14,86)`): terminada con `--exito` (#39ff14) 12,3:1 ·
  error con `--error-texto` (#ff6b6b) 6,0:1 (el `--error` daba 4,43 y no llega
  a AA para texto) · descargando con `--rosa-neon` 4,84:1 · procesando/pausa
  con `--color-num` 6,31:1 · espera/cancelada con `--texto-secundario` 7,62:1.
  Sin porcentaje todavía, la barra es indeterminada (segmento del 35 % que
  corre solo; queda quieto con `prefers-reduced-motion` o `.reducir-efectos`).
  El panel suma el rótulo "Guardar en" y el globo con la ruta completa (el
  texto de la ruta se abrevia con "…"). A 1200 px el lema manuscrito baja a
  18 px y reparte las líneas: "Tu video, en / tus manos ♡".
- **D5 - "Guardado." junto a la tarjeta.** El aviso vivía al pie de Ajustes,
  lejos del control tocado. Ahora el único `role="status"` se mueve a la
  tarjeta del ajuste cambiado (o de la carpeta) y se ubica arriba a la derecha
  en absoluto, así no mueve el layout. Si falla, el mismo aviso va en rojo.
- **D5b - vacío del paso 2.** El cartel de la tarjeta VIDEO queda centrado
  (vertical y horizontal) con el ícono `video.svg` del manifiesto.

**Textos propuestos para la jerga (pendientes de aprobación de Maki)**

Los textos técnicos de Ajustes siguen tal cual; la propuesta es reemplazar
solo lo que un usuario no técnico no entiende:

| Dónde | Texto actual | Propuesto |
|---|---|---|
| Tarjeta Motor | "Origen: PyPI" | "Descargado de la tienda oficial de Python" |
| Tarjeta Motor | "Comprobado: hoy 14:32" | "Revisado: hoy 14:32" |
| Tarjeta Motor | "yt-dlp" (en el aviso de error) | "Motor de descargas" |
| Ajustes | "Idioma de subtítulos" | (queda igual) |
| Ajustes | "Cookies del navegador" | "Usar el inicio de sesión de tu navegador" |
| Ajustes | "Ninguno" (cookies) | "No usar" |
| Ajustes | "Mejorar los links de X con fxtwitter" | "Abrir mejor los links de X" |
| Cola | "Interrumpida" | "Se cortó" |
| Cola | "Reintentar" | "Probar de nuevo" |
| Historial | "Mostrar archivo" | (queda igual) |
| Acerca | "@MakiEzequiel" | (queda igual) |

Nada de esto se aplicó: la spec pide la propuesta, la decisión es de Maki.

**Evidencia**: capturas antes/después a 1600×900, 1200×720 y 880×560 en
`%TEMP%\\opencode\\capturas\\f7d\\` (fuera del repo). Contratos nuevos:
`tests/test_historial_ui.py`, `tests/test_cola_ui.py`, `tests/test_ajustes_ui.py`.

## 3r. Fase 7 - Parte E: el .exe medido y una mejora barata (20/10/2026)

### E1 - cómo está el .exe (antes de tocar nada)

Medido sobre `dist\Miauki YT.exe` (85,4 MB), con una carpeta de datos nueva.
La ventana se detecta enumerando ventanas por PID (no por título) para no
confundirla con una instancia vieja.

| Métrica | Valor |
|---|---|
| Tamaño del `.exe` | 85,4 MB |
| Arranque frío (doble clic → ventana visible) | 1,72 s |
| Arranque caliente (segunda apertura seguida) | 1,48 s |
| Memoria en reposo (proceso de la app, a los 75 s) | ~108-110 MB |
| CPU en 60 s de reposo | 0,03-0,05 s = 0,05-0,08 % de un núcleo |

**Desglose de los 85 MB** (lo que el `.exe` descomprime en `%TEMP%\_MEI…` al
abrir): `ffmpeg.exe` 100,5 MB · Python y librerías (`.dll`/`.pyd`) ~70 MB ·
código + interfaz 5,5 MB · resto 2,2 MB ≈ **178 MB extraídos** que PyInstaller
comprime a 85,4 MB. O sea: **el 80 % del peso es ffmpeg**, y por eso ninguna
optimización de código mueve la aguja de verdad.

Notas:
- La memoria de WebView2 (los procesos `msedgewebview2.exe`) va aparte y no se
  cuenta acá: es el motor del navegador que dibuja la interfaz.
- El `.exe` es onefile: cada apertura descomprime esos 178 MB en `%TEMP%`. Es
  lo que explica el ~1,5 s de arranque. Pasarlo a onedir lo bajaría a ~0,5 s
  pero deja una carpeta con decenas de archivos (peor para "un solo archivo").

### E2 - mejora barata: PNGs del manifiesto más livianos

Sin dependencias nuevas (PIL ya estaba) y **sin UPX** (UPX comprime el binario
pero dispara falsos positivos de antivirus y rompe la reproducibilidad del
hash, así que queda descartado).

| Imagen | Antes | Después | Qué se hizo |
|---|---|---|---|
| `fondo_nebulosa.png` | 1,61 MB | 1,43 MB | reencodado sin pérdida (`optimize`) |
| `Banner…recortado.png` | 1,09 MB | 0,62 MB | 2158×421 → 1538×300 (2× del alto máximo real, 150 px) |
| `Miauki.png` | 1,34 MB | 0,26 MB | 1254×1254 → 512×512 (2× del uso más grande, 168 px) |
| `Botón MIAUK!` | 0,20 MB | 0,20 MB | ya estaba en paleta, no baja |
| **Total** | **4,24 MB** | **2,51 MB** | **-1,73 MB** |

Los atributos `width`/`height` del HTML se actualizaron para que coincidan con
las nuevas medidas (si no, el navegador reserva mal el espacio y salta el layout).

| Métrica | Antes | Después | Δ |
|---|---|---|---|
| `.exe` | 85,4 MB | **84,0 MB** | -1,4 MB (-1,6 %) |
| Arranque frío | 1,72 s | **1,47 s** | -0,25 s |
| Arranque caliente | 1,48 s | **1,42 s** | -0,06 s |
| Memoria en reposo | ~108 MB | ~107-111 MB | igual (dentro del ruido) |

Los originales quedaron respaldados fuera del repo
(`%TEMP%\opencode\respaldos\e2_img\`). Descartado a propósito: bajar la
resolución del fondo a 1600 px (ahorraba 0,2 MB y se notaba en pantallas
grandes) y tocar `ffmpeg.exe` (es la mayor parte del peso, pero cambiarlo
rompe el SHA-256 verificado y la garantía de que descarga bien).

## 3s. Fase 8 - decisiones de Maki: demo y licencia (22/10/2026, aprobado por Maki)

> **REVOCADAS el 22/10/2026 por Maki.** El programa se distribuye gratis: no hay
> demo, licencia, activación, claves ni venta. El texto queda como historia; lo
> vigente está en §3v. La única parte de esta sección que sigue vigente es el
> punto 6 (textos de jerga y del recorrido, aprobados) y el punto 7 (yt-dlp-ejs,
> arte, inglés al final, logos con un profesional, banner intacto).

Fase 8 pedida por Maki: "DEMO Y LICENCIA" + cierre de la Fase 7 (Parte 0).
Registradas ANTES de escribir código, tal como pidió.

1. **Demo = 15 descargas completadas.** Una sola constante, `DEMO_DESCARGAS = 15`,
   en `miauki/core/licencia.py`. Ningún texto ni prueba escribe 15 a mano.
2. **Reemisión: 2 gratis por comprador** (cambio de PC o reinstalación de Windows).
   Desde la tercera corresponde cobrar: la herramienta `tools/emitir_licencia.py`
   lo cuenta, avisa con el número de reemisión y **no bloquea** (Maki decide).
3. **Entrega manual.** Maki cobra por Mercado Pago, efectivo, transferencia y PayPal.
   No hay tienda online, ni servidor, ni activación remota: el comprador manda su
   código de equipo y Maki le devuelve la clave.
4. **"Comprar" abre el Instagram de Maki** (@MakiEzequiel) para que le escriban.
   Se implementa por la lista blanca de enlaces: clave propia `"comprar"` en
   `app_info.ENLACES` (hoy con la misma URL que `"instagram"`), así mañana se
   cambia por una tienda sin tocar código ni interfaz.
5. **La licencia vale para toda la versión 1.x.** La clave lleva la versión mayor
   del producto; la app acepta cualquier 1.x y rechaza 2.x con mensaje propio.
6. **Textos de jerga: aprobados** con los ajustes de la Parte 0.1 (tabla §3q).
   **Textos del recorrido: aprobados tal cual.**
7. **yt-dlp-ejs / intérprete de JavaScript: NO ahora**, solo informe
   (`docs/JS_YOUTUBE.md`). **Arte sin usar: se mueve fuera del proyecto.**
   **Inglés: al final del proyecto.** **Logos de plataformas: los ve un profesional;
   el banner no se toca.**

### Contradicción detectada en el diseño (y cómo se resuelve)

`docs/LICENCIAS_DISENO.md` decía "contador firmado con Ed25519". **Es imposible**:
firmar exige la clave privada, y si la app la lleva adentro cualquiera la extrae y
firma su propio contador. Se implementa, como pidió Maki, un **HMAC-SHA256 con una
clave derivada del código de equipo + una constante de la aplicación**
(PBKDF2 de PyNaCl). Límite honesto: quien sepa leer el `.exe` puede recalcular ese
HMAC en su propia PC; frena la edición con el Bloc de notas y el copiar/pegar de
archivos, no a un reverser. Está en el modelo de amenazas (§3x).

### Desvíos de proceso

- **D3 y D4 comparten commit**, igual que en la Fase 7: los íconos y el manifiesto
  de assets son los mismos archivos y separarlos exigía reescribir historia.
- La Fase 7 ya estaba cerrada y aprobada: la Parte 0 de esta fase **solo** aplica
  los cierres que Maki pidió (textos, test inestable, versiones, CSS, arte, JS,
  entrega); no reabre nada más.

## 3t. Fase 8 - Parte 0: cierres tecnicos (22/10/2026)

### 0.2 - El test inestable (causa encontrada, no "flaky")

Reproduccion: 300 corridas aisladas de
`test_queue_manager.HistorialDeLaCola.test_registra_la_terminada_con_contenedor_real`
-> **14 fallos (4,7 %)**, siempre en la misma linea: `None != {'cambio': True}`
(no habia llegado el evento "historial").

Causa real: **orden de publicacion**, no una carrera del sistema de archivos.
`Cola._bajar_item` marcaba el item `terminada` y emitia "cola" *antes* de escribir
el historial. La prueba esperaba "terminada" y enseguida leia: si el hilo del
trabajador no habia llegado a `historial.agregar`, la lectura veia el estado
viejo.

Correccion (en el codigo, no en la prueba): el historial se escribe **antes** de
publicar `terminada`. Asi "terminada" implica siempre "historial ya intentado"
(si falla la escritura, se registra el aviso y la descarga igual queda terminada).
Resultado: **300/300 aisladas y 20 suites completas (505 tests cada una) sin
fallos**.

### 0.3 - Versiones: comparación numérica

`motor.tupla()` ya convertía "2026.08.19" a (2026, 8, 19) y era lo que usaban
`motor.py` y `actualizador.py`; lo que faltaba era **probar** que nadie lo cambie
por una comparación de texto. Se agregaron tres pruebas de comportamiento (no de
sintaxis) en `test_actualizador.py`:

- "2026.10.2" se ofrece y se aplica sobre "2026.9.30" (como texto habría quedado
  al revés; la prueba lo deja escrito).
- "2026.8.19" contra "2026.08.19" da "al día" (misma versión con cero delante).
- "2026.9.1" se aplica sobre "2026.8.19".

### 0.4 - CSS duplicado: qué era de verdad

Se revisaron los 309 bloques de `layout.css` con un analizador de selectores
repetidos: **23 selectores aparecen más de una vez**, pero 22 son legítimos
(`@media` de ancho, `prefers-reduced-motion`, `.reducir-efectos`, estados
`:focus-visible`/`[hidden]`, pasos de `@keyframes` y `.x.y`). El único duplicado
real era `.video-vacio`, partido en dos bloques seguidos (uno por la Fase 2 y otro
por la Fase 7 D5b): se unificaron sin cambiar ninguna propiedad.

`.col-ruta-texto` ya no estaba duplicado (se corrigió en la Fase 7) y el segundo
`.cola-barra-fill` es la variante de movimiento reducido: se dejan como están.

Regresión visual: 5 pantallas (Inicio, Cola, Historial, Ajustes, Acerca) × 4
tamaños (1600×900, 1355×721, 1200×720, 880×560), capturadas por `PrintWindow`
(renderiza la ventana aunque otra la tape) con el área de cliente exacta, fondo
opaco, sin animaciones y con la fecha del historial fija. **20 de 20 capturas
idénticas píxel a píxel** (`%TEMP%\opencode\capturas\f8_0_5\`).

### 0.5 - Arte sin usar: movido, no borrado

Destino: `C:\Users\Maki\Desktop\PROYECTOS\Miauki YT\Arte original\` (fuera del repo,
junto al proyecto). Se copió, se verificó el **SHA-256 de cada copia** y recién
entonces se sacó del repo con `git rm`. Nada del manifiesto se tocó.

| Archivo | Tamaño | SHA-256 (primeros 16) |
|---|---|---|
| Banner neón de Miauki este OK.png | 1.229.616 B | 3dbe606502753f2f… |
| Botón-neón-MIAUK_con-huella ico.ico | 135.230 B | 68e45511404578d8… |
| fondo nebulosa.png | 1.687.589 B | 0228dcd6eb8df14d… |
| Miauki_ Gatos Kawaii y Neón Gaming ORIGI.png | 1.198.061 B | d92cf98edefc3078… |
| miauki_fondo_nebulosa_suave.png | 1.132.226 B | c80bb6ffafb015a8… |

Total: **5,13 MB** y 5 archivos. Como ninguno estaba en `tools/assets_manifest.txt`,
el `.exe` no cambia de tamaño: se sacan del repositorio, no del paquete.

### 0.6 - JavaScript para YouTube: informe y error amable

Informe completo en `docs/JS_YOUTUBE.md` (no se agregó nada al `.exe`). Datos
medidos: `yt-dlp-ejs` 0.8.0 pesa **0,05 MB**; el intérprete (Node LTS 24.22.1 o
Deno 2.9.8) pesa **36–41 MB comprimido**, así que el `.exe` pasaría de 84,0 MB a
~120 MB.

De paso se corrigió un texto que quedaba desalineado con la 0.1: el mensaje de
"pide iniciar sesión" decía *Ajustes → Cookies* y el ajuste ahora se llama "Usar
el inicio de sesión de tu navegador". Se actualizó el mensaje y su test.

### 0.7 - Entrega permanente

El zip de prueba se generaba en `%TEMP%`, que Windows limpia. Ahora
`python tools/armar_entrega.py` lo deja en
`C:\Users\Maki\Desktop\PROYECTOS\Miauki YT\Entrega\` (fuera del repo), con el
mismo contenido que antes: `Miauki YT.exe` + `LICENCIAS.txt`. Se regeneró y quedó
en 83,5 MB. `docs/PRUEBA_EXE.md` apunta a la carpeta nueva.

## 3v. Fase 9 - decisiones de Maki: gratis, sin licencia (22/10/2026, decidido por Maki)

Registradas **antes** de escribir código, como pidió Maki.

1. **El programa se distribuye GRATIS.** Se descarta todo lo de venta: licencia,
   activación, demo de 15 descargas, claves, herramientas del vendedor, documentos
   de ventas y cualquier "versión de prueba" como evaluación. Las decisiones de
   licencia de §3s quedan **revocadas** (el texto se conserva como historia).
   Lo de §3t (Parte 0 de la Fase 8) sigue vigente.
2. **"¿Por qué se cerró sola la app?": se deja de investigar** y sale de
   `PENDIENTES.md`.
3. **Inglés al final del proyecto.** **Logos de plataformas:** los consulta Maki
   con un profesional. El banner no se toca.
4. **Cómo se deshace la venta (decisión técnica de esta sesión):** `git revert`
   de los 7 commits de la Fase 8 (A-D) en orden inverso y en **un solo commit**
   (`c47656f`), no borrado manual. Motivo: deja el árbol **idéntico** a `cfff68d`
   (fin de la Parte 0), conserva la historia y no puede olvidarse ningún archivo;
   el borrado manual dependía de una lista a mano de 39 archivos. Los commits de
   la Parte 0 no se tocan porque son anteriores.
5. **Resguardo:** etiqueta `pre-gratis` sobre `5d213d0`. Volver atrás =
   `git checkout pre-gratis` (mirar) o `git reset --hard pre-gratis` (volver,
   perdiendo lo posterior). No se reescribió el historial.
6. **Guardia permanente:** un test falla si vuelve a aparecer cualquier rastro
   de licencia/venta en la app, la interfaz, los textos o `requirements.txt`
   (`tests/test_sin_licencia.py`). No marca las licencias de terceros
   (`LICENCIAS.txt`, "Licencias de terceros" de Acerca, docs de licencias).
7. **Registro de Windows y carpeta de datos:** no se tocan.

### Cierre de la Parte A (22/10/2026)

- **Suite:** 515 tests OK. Antes de la Parte A había 625: se fueron **110**
  (todos de licencia: `test_cripto`, `test_licencia`, `test_licencia_ui`,
  `test_licencias_herramientas`, `test_licencias_privadas` y los agregados de
  licencia en `test_queue_manager` / `test_zz_datos_reales`) y se sumaron **4**
  nuevos de la guardia (`test_sin_licencia`). Neto: **-106**.
- **Selftest:** 6/6 (volvieron a 6 al sacar "criptografía" y "licencia").
- **`.exe`:** 84,0 MB (88.080.320 bytes). Arranque medido de proceso a ventana
  visible: **1,51 s en frío** y **1,43 s en caliente**. La marca anterior de
  2,17 s se tomó con otro método (esperaba a la interfaz cargada), así que no
  son comparables; el tamaño sí: 84,3 → 84,0 MB.
- **Entrega:** `Entrega\Miauki YT v1.0.0 - Windows.zip` (83,5 MB). Se borró el
  zip viejo "SOLO PRUEBA".

## 3w. Fase 9 - Parte B: mejoras pedidas por Maki (22/10/2026)

Lo que pidió Maki, cómo se resolvió y con qué prueba. Los textos nuevos están en
la lista de aprobación de `PENDIENTES.md`.

1. **B1 - Fotos de X (una o varias).** Dos causas: (a) el link suelto de una
   foto (`pbs.twimg.com/media/...`) caía en "otro sitio" y se mandaba a yt-dlp,
   que no lo entiende; ahora se reconoce como imagen sola
   (`images.es_imagen_x_directa`) y no pasa por el motor de video. (b) los links
   con el id en otro lugar (`/mediaviewer/`, `?status_id=`) no lo encontraban;
   `id_tweet` ahora acepta esas formas. Las fotos de un post con varias salen
   todas y se descargan todas (probado con el fixture real recortado
   `tests/fixtures/x_graphql_foto_real.json`, 3 fotos).
2. **B2 - Post que pide sesión.** X devuelve una "lápida" vacía cuando el post
   necesita sesión (contenido sensible): antes se leía como "tweet borrado".
   Ahora da `requiere_sesion` con un mensaje que no afirma de más ("puede ser
   para mayores o de una cuenta protegida") y la pantalla de error muestra el
   atajo **"Ir a Ajustes"**. Además, si la vía de imágenes falla por sesión, ese
   mensaje gana al error crudo de yt-dlp.
3. **B2 - Cookies del navegador.** Se sumaron dos códigos nuevos
   (`cookies_bloqueadas`, `cookies_no_encontradas`) con su mensaje claro. En
   esta PC, **Edge falla siempre**: `Failed to decrypt with DPAPI` (problema
   conocido de yt-dlp, issue 10927: las versiones nuevas de Chrome/Edge cifran
   las cookies con una clave que yt-dlp no puede leer). Firefox y Chrome no
   están instalados acá, así que ese camino no se pudo probar en vivo.
   Propuesta para el informe: aceptar un `cookies.txt` exportado a mano; **no
   se implementó** porque Maki no lo pidió.
4. **B3 - Post de solo imágenes.** Video y Música quedan apagados de verdad
   (`disabled` + `aria-disabled`) y aparece una nota corta que explica por qué.
   Quién decide es el backend (`tipos` del análisis), no la interfaz.
5. **B4 y B5 - Tamaños.** Miniatura +35 % (`--w-mini` 116 → 157, compacto
   sigue en 104) y botón MIAUK al doble en ventanas altas (`--h-btn-miauk`
   76 → 152), escalón intermedio de 88 px en altura media (≤760) y 48 px en la
   baja (≤640), como estaba. Para pagar esos 152 + 157 px de alto sin scroll, se
   recortó aire del layout con tokens: `.central` gap 12 → 8 (`--esp-2`),
   `.tarjeta` vertical 12 → 8, `.video-fila` vertical 8 → 4 (`--esp-1`), y a
   ≤760 la ayuda tenue pasa a sr-only (ya pasaba a ≤640). Medido: 1600×900 y
   1200×720 dan **scroll 0** en vacío, video e imagen; 1355×721 da 0/0/**16**
   en imagen (la grilla de 3 fotos ya no entraba antes: era 13); 880×560 sigue
   en 147/147/169, igual que la referencia.
6. **B6 - Barra flotante.** El doble de grande (1040×96, texto 28 px; en ancho
   ≤999 el texto baja a 20 px, el × a 56 px y la onda decorativa se esconde) y
   **arrastrable**: asa con cursor de agarre, pointer events con captura,
   flechas del teclado en el asa enfocada (10 px, 40 con Shift), re-acote al
   cambiar el tamaño de la ventana, el conteo de 10 s **se pausa mientras se
   arrastra**, × sigue cerrando, cada barra nueva vuelve al origen y respeta
   `prefers-reduced-motion`.
7. **Un solo commit por motor y otro por interfaz** (no cinco): los cambios de
   B3 a B6 comparten los mismos archivos (`tokens.css`, `layout.css`, `app.js`),
   así que separarlos exigía partir líneas del mismo archivo a mano; el riesgo
   de romper algo era mayor que el beneficio. Quedan `fe90150` (motor, B1+B2) y
   `7e4e345` (interfaz, B3-B6).
8. **Suite:** 549 tests OK (eran 515): +34 (`test_images` llega a 35,
   `test_ui_fase9` nuevo con 23, más los de errores y el de análisis cambiado).
   Selftest 6/6 y `tools/check_a11y_vivo.py` sin nombres faltantes (el asa se
   llama "Mover el aviso de link (flechas del teclado)").
9. **Pendiente anotado, no arreglado:** con el doble de tamaño, la barra en su
   posición de origen (arriba, centrada) tapa buena parte del banner. Se puede
   mover con el mouse, pero la posición inicial quedó como estaba; ver
   `PENDIENTES.md`.

## 3x. Fase 9 - la barra flotante baja un quinto y nace abajo a la derecha (23/10/2026, decidido por Maki)

Maki vio la barra al doble y le pareció **demasiado grande**, y en su posición
vieja (arriba, centrada) tapaba el banner. Estas tres decisiones se registran
antes de tocar código y **reemplazan el "doble de tamaño"** del punto B6 de §3w.

1. **Tamaño: ×0,8 del doble actual** (redondeado a píxel entero). Es un quinto
   menos de todo: alto, ancho, texto, íconos y asa. Los tokens de la barra en
   `tokens.css` quedan así:

   | Token | Antes (doble) | Ahora |
   |---|---|---|
   | `--h-input-barra` | 80 px | **64 px** |
   | `--w-barra` | 1040 px | **832 px** |
   | `--h-barra` | 96 px | **77 px** |
   | `--fs-barra` | 1,75 rem (28 px) | **1,4 rem (22,4 px)** |
   | `--ico-barra` | 44 px | **35 px** |
   | `--img-barra` | 52 px | **42 px** |
   | `--x-barra` | 72 px | **58 px** |
   | `--asa-barra` | 28 px | **22 px** |

2. **Posición de origen: abajo a la derecha**, con el margen estándar de la app
   contra el borde derecho e inferior del área visible, para molestar lo menos
   posible. Sigue siendo arrastrable y cada barra nueva vuelve a ese origen. El
   ancho es el menor entre `--w-barra` y el ancho visible menos los márgenes: a
   880 px de ancho no puede desbordar. Si se redimensiona la ventana se
   re-acota, y si la barra estaba en su origen sigue anclada a la esquina.
3. **Lo demás de B6 no cambia**: arrastre con pointer events, límites dentro de
   la ventana, asa con flechas del teclado, pausa del conteo de 10 s mientras se
   arrastra, × que cierra, `prefers-reduced-motion`, la regla de `[hidden]` vs
   `display:flex` y `inert`.

También en esta tanda, por pedido de Maki: **archivo de cookies** en Ajustes
(B2b), como reemplazo del botón "Elegir…" de la v2.6. Se guarda **solo la ruta**
en los ajustes, nunca una copia del archivo ni su contenido en logs.

### Cierre de la Parte B (23/10/2026)

Lo que quedó implementado y probado, con las decisiones que lo respaldan:

- **Barra ×0,8 y origen abajo a la derecha**: tokens de la tabla 1, anclaje con
  `--esp-4` contra los bordes derecho e inferior, ancho
  `min(--w-barra, 100vw − 2 márgenes)`, re-acote y reanclaje al redimensionar.
  Medido en vivo: 832×82 px y 16 px de margen en los cuatro tamaños; a 880 px de
  ancho entra sin desbordar. Tapa el selector de calidad (fila del Paso 3) en
  1600×900, 1355×721 y 1200×720 mientras está visible; se arrastra o se espera
  a que se cierre sola. No tapa el botón MIAUK.
- **Scroll 0 manda**: a 1355×721 un post de solo imágenes desbordaba 16 px. Se
  cerró bajando el relleno vertical de las tarjetas (6→4 px) y el margen superior
  de la columna (24→16 px) **solo en el escalón de altura ≤760 px**. Ahora 0 px
  en 1600×900, 1355×721 y 1200×720 con video y con 3 fotos; en 880×560 queda
  scroll interno (147/169 px), que es el comportamiento esperado.
- **Archivo de cookies (B2b)**: un solo módulo (`miauki/core/cookies.py`) decide
  qué cookies van a yt-dlp (archivo gana sobre navegador) y cuáles se leen para
  las vías de imágenes de X (solo `x.com`/`twitter.com`, en memoria). Validación
  con `http.cookiejar` (formato Netscape con cabecera, tope de 5 MB), botones
  «Elegir archivo…» y «Quitar», aviso de privacidad, y guía en `docs/COOKIES.md`.
  Un archivo borrado o inválido da error amable y lleva a Ajustes en vez de un
  "pide iniciar sesión" sin explicación. Los valores de las cookies no se
  escriben en ajustes, logs ni tests.
- **Entrega**: `tools/armar_entrega.py` ahora compara la interfaz embebida del
  `.exe` con la del repo y **no arma el zip** si hay diferencias (un cambio de
  interfaz sin recompilar se detecta antes de repartir).

## 4. Requisitos de producto (resumen)

- Barra lateral con **EXACTAMENTE 5** secciones: Inicio, Cola de Descargas, Historial, Ajustes, Acerca de...
- **Inicio**: Paso 1 PEGÁ EL LINK (campo + "Analizar" con degradado magenta + botón imagen "MIAUK!" de Icos, apagado hasta analizar; único botón de descarga) → Paso 2 VIDEO (miniatura, título, duración, canal, sitio, selector Video/Audio/Imagen) → Paso 3 CALIDAD (chips según lo que ofrece el link: video 480p–8K nada debajo de 480p salvo video nativo inferior; audio 320/256/128 MP3; imagen según el post; recuadro Formato/Tamaño/Tiempo/Peso total descargado). Ayuda: "cada click en MIAUK! agrega una descarga a la cola". Sin botón de descarga duplicado.
- **Imágenes**: al menos lo que hacía la v2.6 (X con FxTwitter + Facebook vía yt-dlp). Multi-imagen → proponer en la Fase 3 si conviene elegir cuáles.
- **Barra de portapapeles**: solo con link soportado; "Wow... un link: ¿Lo usamos?" + botón "Miauk" + "×"; se oculta a los 10 s; el "Miauk" analiza (NO descarga).
- **Cola**: hasta 10 en espera, 1 activa a la vez; estados en espera/descargando/pausa/procesando/terminada/error/cancelada; "×" cancela (y si se aprieta de nuevo sobre una cancelada, la borra); reintento circular; pausa conservando `.part`; cada ítem con miniatura, título, estado, barra con degradado, MB/s y tiempo restante; contador en la barra lateral.
- **Historial**: auto-limpieza a 30 días; abrir archivo, abrir carpeta (deshabilitado si el archivo se movió), volver a descargar.
- **Ajustes**: sección dentro de la ventana (no ventana aparte): carpeta de descargas, subtítulos es/en, cookies (Ninguna/Chrome/Edge/Firefox), FxTwitter (activado por defecto), registro/logs con "Abrir carpeta", detalles técnicos (ffmpeg y versión de yt-dlp), Idioma (Español por defecto, estructura preparada para más idiomas).
- **Acerca de**: datos de `app_info.py`.
- **Panel derecho** de Inicio: sitios soportados, indicador de subtítulos, frases decorativas.
- **General**: notificación de Windows al terminar + "Abrir carpeta"; errores SIEMPRE amables en español, trazas solo al log.

## 5. Diseño

- Referencia: `docs/referencia/Idea-de-MIAUKI-YT.png` (1600×900). La ventana debe verse CASI IDÉNTICA, con las correcciones del prompt.
- Fondo: nebulosa violeta/índigo UNA SOLA para toda la app (`fondo_nebulosa.png`, cover, fijo). Prohibidos destellos extra y cuadros sólidos que corten el fondo: todo lo que va encima es translúcido.
- Barra lateral ~10% con píldora activa degradada; abajo gatito + "Las mejores descargas, siempre ♥".
- Encabezado ~20%: logo MIAUKI neón + lema manuscrito, píldora "⚡ Descargador de videos y audio" + íconos de redes + "+1800 sitios", gato grande a la derecha fundido con el fondo (PNG con transparencia; si hay fondo opaco, resolver con `mix-blend-mode`/`mask-image` o procesando la imagen).
- 3 tarjetas de vidrio (radio ~18–20 px, borde violeta fino con brillo, `backdrop-filter`), insignias 1/2/3 con anillo luminoso.
- Columna derecha ~18% con frases manuscritas, lista de sitios y "Subtítulos..."; barra inferior con el link detectado.
- Tipografía: **Fredoka** (interfaz) + **Caveat** (manuscrita, ya verificada en assets).
- Colores de partida (afinar en `tokens.css`): fondo `#07041a`; tarjetas `rgba(40,18,96,0.35)`; bordes `rgba(168,85,247,0.45)`; texto `#f3eaff` / `#b9a5e6`; degradado botones `#7c3aed → #c026d3`. Estados: éxito **verde neón** (esto cambia la decisión vieja de "sin verde"), error rojo fuerte, aviso en la paleta violeta/magenta.
- **Personalización**: NADA hardcodeado en componentes; todo en `tokens.css`.
- Errores de la v2.6 que NO se repiten: fondo cortado en pedazos, banner pisando el contenido de Cola/Ajustes, cuadros sólidos detrás de textos, bordes violeta gruesos por todos lados, mucho espacio vacío.
- Ventana: inicial ~1200×720 (o 85% del área útil), mínima ~880×560 (proponer finales tras probar). 3 niveles responsive: amplio ≥1280, medio 1000–1279, compacto <1000 (columna derecha oculta). Scroll solo si hace falta. Probar a 880×560 / 1200×720 / 1600×900 / 1920×1080 y escalas 100/125/150%. Respetar `prefers-reduced-motion`.

## 6. Reglas de arquitectura y calidad

- `api.py`: puente delgado; SIEMPRE devuelve `{ok, data|error}`; nunca excepciones a la interfaz.
- `events.py`: eventos Python→interfaz seguros entre hilos, datos con `json.dumps` (nunca concatener JS con texto).
- La interfaz espera `pywebviewready` antes de llamar a Python.
- Descargas en hilos; cancelar corta de verdad y limpia temporales (salvo `.part` en pausa).
- Escritura de config/historial atómica. Instancia única. Logs con rotación.
- `--selftest`: ffmpeg, yt-dlp, carpetas, WebView2 y fuente de interfaz (embebida/externa).
- Tests mínimos: selección de calidades, máquina de estados de la cola (con pausa), limpieza del historial, detección de URLs.
- Seguridad: CSP estricta, URLs validadas, nada de shell, carpeta `ui` externa tratada como código local de confianza.
- No tocar archivos fuera de la carpeta del proyecto y de la de datos del usuario.

## 7. Plan de fases

- **Fase 0** — Preparación y relevamiento. ✅ (12/10/2026)
- **Fase 1** — Esqueleto técnico + prueba temprana de .exe.
- **Fase 2** — Interfaz estática con datos de mentira (2A base/fondo/tokens/layout; 2B barra lateral y encabezado; 2C tarjetas 1-2-3; 2D panel derecho y barra inferior; 2E Cola/Historial/Ajustes/Acerca estáticas; 2F responsive y pulido). Comparar con la referencia en cada sub-paso.
- **Fase 3** — Backend: config, logs, errores, modelos, analizador de links e imágenes (X y Facebook).
- **Fase 4** — Backend: descargas, cola con pausa/cancelar/reintentar/borrar, ffmpeg, progreso, historial.
- **Fase 5** — Conectar interfaz y backend: Analizar → Video → Calidad → MIAUK! → progreso.
- **Fase 6** — Cola, Historial, Ajustes y Acerca conectados + barra de portapapeles.
- **Fase 7** — Pulido UX: estados vacíos, errores amables, animaciones, accesibilidad, atajos (Ctrl+V), notificaciones.
- **Fase 8** — Robustez: sin internet, pruebas en Windows 10/11 limpios, instalación automática de WebView2. (La actualización de yt-dlp se movió a después de la Fase 4 — A9 de la Parte B, ver `tasks/plan.md`.)
- **Fase 9** — Empaquetado final, ícono, metadatos, prueba en PC limpia, tamaño y arranque.

## 8. Skills (cómo se usan)

- **Base de todas las fases**: using-agent-skills, spec-driven-development, incremental-implementation, source-driven-development (doc oficial de pywebview/WebView2/yt-dlp/PyInstaller, no memoria), git-workflow-and-versioning, documentation-and-adrs.
- **Planificación/migración (Fase 0 y arranque de cada fase)**: planning-and-task-breakdown, deprecation-and-migration.
- **Interfaz (2, 5, 6, 7)**: ui-ux-pro-max, design-system, frontend-ui-engineering, ui-styling (solo CSS puro, NO Tailwind/shadcn), browser-testing-with-devtools, performance-optimization.
- **Backend (1, 3, 4, 6, 8)**: api-and-interface-design, test-driven-development, security-and-hardening, observability-and-instrumentation, debugging-and-error-recovery.
- **Cierre de cada fase**: code-review-and-quality, code-simplification, ponytail-review + ponytail-audit (leer ponytail-help primero; ponytail-debt solo en Fases 7-9 si aplica). `ponytail/` y `ponytail@latest/` son la misma skill.
- **Entrega (Fase 9)**: shipping-and-launch, performance-optimization, code-review-and-quality.
- **Prohibidas**: todas las de marketing/copy/ventas (ad-copy, ad-creative, banner-design, brand, compliance-checker, copychief, copywriting, cro, direct-response-copy, facebook-ads, landing-page-copy, lead-magnet, marketing-psychology, offers, ogilvy-copywriting, pricing, slides, social, stop-slop, tus-recursos-digitales-sales, design) y por ahora: interview-me, idea-refine, archify, constraint-driven-development, doubt-driven-development, context-engineering, ci-cd-and-automation, translation, customize-opencode (justificar en 1 línea antes de usar alguna).
- Regla: si dos skills se contradicen, elegir la más adecuada al proyecto y explicar en una línea. No instalar skills nuevas.

## 9. Datos de prueba

- YouTube: `https://www.youtube.com/watch?v=BaW_jenozKc` (~9 s), "Me at the zoo" (`jNQXAC9IVRw`, 240p), merge 1080p `RpOlTN2xdwg`.
- X: el link `hrX3pmFJ_i8` aparece en capturas viejas.
- Borrar SOLO los archivos de prueba que cree la app; los videos del usuario no se tocan.

## 3z. Tandas 16–18/11/2026 — decisiones y cierres

- **Playlists (16/11):** se aprueba soporte para playlists de YouTube y YouTube Music. Máximo 100 videos (protección de memoria). Videos privados/eliminados: saltearlos y seguir, PERO mostrar resumen que explique el porqué con catálogo de AL MENOS 10 causas (se implementaron 19). El video salteado no corta la lista. UI: pantalla con casillas, seleccionar todo y calidad global; encolado por video `[N/T]`.
- **Ajustes UI (17/11):** botones "Cambiar" y "Abrir carpeta" de Guardar en (Inicio) conectados al API (antes muertos). Sincronización de carpeta Ajustes↔Inicio al instante. Playlists: tope 500, descarga por bloques automáticos de 200 ("Bloque X/Y"; sin clics extra). Refresh manual con dos flechas que recarga la app al instante (sin detección automática). × en vista previa: oculta para esa tarjeta, vuelve al re-analizar el mismo link.
- **Archivos y cola (18/11):** el archivo descargado (mp3/mp4) y el historial conservan el título real, sin prefijos de bloque (el `[Bloque X/Y] [N/T]` queda solo en la Cola). Botones globales: Pausar todo (congela activas + espera), Reanudar todo, Cancelar todo (borra lo pendiente; lo descargado queda) y tacho rojo que vacía el historial de la cola (terminados/cancelados/fallados; NO toca archivos en disco). Contador de activas en verde. Fuente: ajuste `tamano_fuente` normal/grande (+10% en toda la interfaz, clase `font-grande` en la raíz). Acerca de: +10% siempre (texto y cara del gatito) con tope 1.17 combinado (1.1 × 1.0636) para nunca llegar a 1.20.

## 3aa. Tanda 19/11/2026 — decisiones y cierres

- **Instagram, historias:** decisión de Maki de usar el motor integrado (opción A, yt-dlp `InstagramStoryIE`) en vez de agregar instaloader (se evaluó: licencia MIT, pero mismo requisito de sesión y más peso/mantenimiento). Errores de historias mapeados: "You need to log in to access this content" → `requiere_sesion`; "This content is unreachable" → `video_eliminado`. Historias solo-imagen se tratan como imagen.
- **Instagram, cuentas públicas:** sí a que `instagram.com/usuario` liste reels/publicaciones como playlist (tope 500, tandas de 200). Limitación conocida: el extractor de perfiles de yt-dlp 2026.8.19 está con `_WORKING=False` ("Unable to extract data") → requiere actualizar el motor.
- **URLs relajadas:** sí a aceptar `www.` sin esquema y dominios con ruta (`minombre.io/video`) anteponiendo `https://`; se respeta `http://`. Un dominio sin ruta se rechaza (falso positivo en frases). Mensaje de error actualizado en es/en.
- Commits: `8d19d9d`…`d3b8f8a` (12). Suite 693; exe SHA `101c2fa`.

## 3ab. Tanda 20/11/2026 — decisiones y cierres

- **Recorrido guiado:** paso 8 nuevo "Refrescar", que señala el botón de la columna derecha (clave `[data-refresh]`); textos es/en `recorrido.p8.*`. Los pasos 1–7 quedan igual.
- **Cartel suave si la app se traba:** watchdog en el frontend (`miauki/ui/js/vigia.js`, módulo aparte sin DOM) que consulta el puente cada 5 s; a los 10 s sin respuesta, y solo si no hay análisis en curso ni descargas activas, muestra un cartel con **Refrescar** (recarga la ventana) y **Seguir esperando**. Si el puente vuelve a contestar, el cartel se retira solo. Probado con Node sobre el módulo real (4 casos) más el cableado en `app.js`.
- **Paso 2 de Inicio:** la tarjeta de vista previa pasa de "Video" a **"Previsualización"** (en: "Preview").
- **Playlist:** contador `.pl-conteo` al doble de `--texto-sm` y botón MIAUK a **236 px** (antes 118). En ventanas de hasta 760 px de alto baja a 1,5× (177 px) y en ventanas de hasta 640 px de alto o ancho a 1,25× (148 px), para no comerse la lista.
- **Verificación anti-bot de YouTube:** código propio `youtube_verificacion_bot` con mensaje propio (ya no se informa como "iniciar sesión", porque las cookies no lo resuelven). Reintento automático 2 veces con 3 s de espera, tanto al analizar como al descargar; el resto de los errores no se reintenta y la cancelación/pausa nunca se traga. Además, cuando yt-dlp ignora el error y devuelve vacío, se recupera el error real del logger para mapearlo (antes salía "El motor no devolvió datos"). Un link `youtube.com/playlist` sin código de lista da mensaje claro (`playlist_sin_id`).
- Commits: `8fcff3c`, `fd9cb53`, `caf4d94`, `723d39f`, `08c2de8` (5). Suite 713 (+1 fallo de entorno preexistente en `test_motor::Reversa`); exe 89.678.089 bytes, SHA-256 `04933A22…`.

## 3y. Tanda post-v1.0 — decisiones y cierres (07–09/11/2026)

- **Banner:** se aprueba el "esto OK 2" sin logos de redes (reemplaza al anterior; centrado, sin pérdida de calidad).
- **Calidades:** listar todas las alturas hasta 8K; opciones separadas mp4/mkv por altura; quitar el peso del panel; opción "Original" para formatos sin metadatos (Snapchat spotlight).
- **Instagram/Acerca:** nuevo usuario @tusrecursosdigitaless; texto legal sin afiliación.
- **Cookies (Paso C):** ayuda desplegable debajo del botón de Ajustes, 5 pasos; puntos 4–5 redactados por Maki; ejemplo con directorio de Chrome. Commit `4373151`.
- **Selector de calidades:** el grupo principal muestra SOLO las recomendadas (Mejor/Equilibrada/Liviana); "Más opciones" muestra todas; opción elegida única compartida y sincronizada entre ambos paneles.
- **Números 1/2/3:** círculo 56 px, borde 3 px `#f0abfc`, glow `rgba(196,81,253,0.7)`, Caveat 34 px weight 700, centrado óptico (translateX -0.12em); desvío ≤1px vs referencia.
- **X:** posts con video (NSFW incluidos) ya no se descartan; tres vías incluyendo fxtwitter público sin cookies. Calidades completas con peso real (HEAD), duración, miniatura y mp4; vista previa más grande; Cola con sitio, formato, peso total y fecha/hora.
- **Licencia:** GPL 3.0 "libre para siempre". Donación en Acerca de + barra lateral (discreto): PayPal paypal.me/ezequielgottwald y alias makiezequiel.naranja; sin cripto.
- **Idioma:** automático según idioma de Windows (`navigator.language`) con fallback `?idioma=en`; 86 claves idénticas en strings.es.js/strings.en.js.
- **Instalador:** NO se crea (decisión de Maki); primero traducción completa, después installer.
- **Douyin:** descartado por decisión de Maki (requiere cookies frescas); pendiente mensaje amable.
- **Snapchat:** whitelist CDN bolt-gcdn.sc-cdn.net / sc-cdn.net; peso real vía HEAD (peso_aprox=False); duración no disponible (no inventar).

## 3ac. Tanda 20/11/2026 #2 — decisiones y cierres

- **Calidad máxima playlist (híbrida):** sondeo en paralelo (~4 workers, 35 s, caché 5 min) de la máxima real por video. Todas iguales → se ofrece esa máxima (8K/4K/2K/Full HD); distintas → solo 1080p y salteados `calidad_insuficiente_playlist` para los <1080p; sondeo incompleto → fallback "Mejor calidad".
- **Límite playlist 500→600** (`validacion.MAX_PLAYLIST`), bloques de 200 intactos.
- **Música solo 320 kbps** (`_musica` devuelve una única opción).
- Commits: `beccc87`, `71b798c`, `21afb59`. Suite 718 (+1 entorno `test_motor::Reversa`); exe SHA `0c4a243d…` (raíz = dist).

## 3ad. Tanda 20/11/2026 #2 — corrección (playlist mixta)

- **Playlist mixta:** se elimina el salteo por calidad. La regla "mixta → solo 1080p y saltear <1080p" rompía playlists de música (videos lyric con máxima 720p/480p). Nueva regla (aprobada por Maki): si todas las máximas son iguales se ofrece esa máxima real; si son distintas, todos los videos se descargan en su mejor calidad disponible y el menú ofrece la máxima real de la lista + inferiores + Música. Solo se saltean links caídos/privados/eliminados.
- Commits: fix en `beccc87`→nuevo commit (ver HEAD). Suite 718 (+1 entorno); exe SHA `e29b924c…`.

## 3ae. Tanda 20/11/2026 #2 — Calidad Máxima en playlist mixta y cancelación

- **Playlist mixta:** el menú ahora ofrece "Calidad Máxima" como opción por defecto (baja cada video en su mayor calidad real) + opciones fijas inferiores (1080/720/480) + Música. En playlists uniformes se mantienen todas las opciones hasta la máxima real (8K/4K/2K/Full HD).
- **Cancelación en cola:** se arregló que cancelar no tuviera efecto durante el postproceso (ffmpeg merge/mp3): el descargador ahora verifica la señal de cancelar con la ruta final y borra el archivo si corresponde. Además, cancelar responde durante el reintento anti-bot (antes dormía 3 s sin escuchar). Se estabilizó el mock de tests de cola (ventana de escucha) para eliminar una carrera.
- **Exe reconstruido (21/11/2026):** luego de los ajustes de UI (pantalla playlist: título "Lista de archivos para descargar", nombre en magenta neón, barra acortada con MIAUK! en la misma línea, contador verde), se rearmó el .exe con `tools/build_exe.py`. Verificado: raíz = dist, SHA `c7fa6695…`; suite 719 passed (+1 entorno `test_motor::Reversa`) y `test_sin_licencia` 15 passed con el exe nuevo. Commit + tag checkpoint-20261121-1.

## 3af. Ajustes 21/11/2026

- **Pausa/reanudar:** `nombre_base_libre` ya no cuenta los temporales de yt-dlp (.part/.ytdl/.temp/fragmentos .fNNN) como ocupados → al reanudar se reutiliza el mismo nombre y la descarga continúa (antes elegía "X (2)" y reiniciaba de 0 dejando el .part viejo). Además, al completar una descarga se limpian parciales hermanos del archivo final (`limpiar_restos_del_final`).
- **Falsos eliminados:** reglas más finas en `errors.py`: "removed by the uploader"/"has been removed"/"deleted video" → `video_eliminado`; "members only"/"sign in to watch" → `requiere_sesion`; "unusual traffic"/captcha/recaptcha → `youtube_verificacion_bot`; "try again later" → `tiempo_agotado`. En YouTube, un `video_eliminado` pasajero se reintenta una vez de inmediato (analizador y descargador) antes de declararlo eliminado.
- **Reintentar ("Probar de nuevo"):** limpia temporales viejos y reanaliza el link (silencioso, fuera del candado) para refrescar el selector/calidad antes de reencolar.
- **Historial:** tope de miniatura 8 KB → 300 KB (las portadas reales quedan guardadas); si el archivo no está o no hay portada, se muestra una de las tres gatitas (Gatita miauki1/2/3.png) elegida de forma estable por id. Assets nuevos en `tools/assets_manifest.txt`.
- **Privacidad:** aviso en Ajustes y Acerca de (sin telemetría, todo local).
- Commits: `4ca3918`, `4f94886`, `9ee5580`, `e8b42f7`, `0264ed6`. Suite 730 passed (+1 entorno `test_motor::Reversa`). **Exe NO reconstruido** (por pedido de Maki): `test_sin_licencia` queda rojo hasta el rebuild.

## 3ag. Ajustes de UI + build 21/11/2026

- **Barra detectora -20%:** `--h-campo` 46→37, `--h-btn-miauk` 152→122 (escalones 88→70, 48→38).
- **Acerca de:** marca MIAUKI YT estilizada (Caveat 36px, degradado violeta→magenta→rosa con recorte de texto).
- **Spec:** se agregan `Gatita miauki1/2/3.png` a los datas (para que el exe las incluya).
- **Exe reconstruido** SHA `494009c2…` (raíz=dist); suite 731 (+1 entorno `test_motor::Reversa`); `test_sin_licencia` verde de nuevo.

## 3ah. Fix cancelar todo y errores de playlist 21/11/2026

- **Faltaba `cancelar_todo` en el puente** (`api.py`): el botón global de la Cola lo llamaba pero no existía → no cancelaba nada. Agregado con `@seguro`. Comportamiento: todas las activas (espera/descargando/procesando/pausa) → `cancelada`, quedan en la cola hasta el tacho. Test de regresión del flujo completo.
- **Selectores de playlist compatibles MP4:** `selectorPlaylist` en `app.js` ahora pide primero `bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]` (con respaldos) en vez de `bestvideo+bestaudio`: evitaba que la fusión a MP4 fallara con audio Opus/video VP9/AV1 (causa de "ocurrió algo inesperado" con Calidad Máxima).
- **Exe reconstruido** SHA `e4886542…` (raíz=dist). Suite 731 (+1 entorno `test_motor::Reversa`); `test_sin_licencia` verde.

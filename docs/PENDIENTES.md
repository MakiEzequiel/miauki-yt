# PENDIENTES — Miauki YT v1.0

Actualizado: 22/10/2026 (Fase 9 Parte B cerrada; ver §3w de DECISIONES y la sección (g) al final para lo que queda).
Se actualiza en cada fase. Fuentes: especificación de cada fase + decisiones de Maki.

## (0) Fase 5 — trabajo pendiente (guardado 19/10/2026; **cerrado el 20/10/2026**)

Estado del repo: limpio. Commits de la tanda: `d4cd8e2` (coma decimal), `9c958c1` (pulido de Inicio), `41430b7` (foco/progreso de la Cola), `25fab9c` (decisiones §3f), B1 (portapapeles), `41146b6` (B2 barra), `f3a25fc` (B3/B4/B5 + "Quitar" y "Limpiar"), `4fd2e6f` (la barra analiza), `f82c860` (backend al día) y `8e778d5` (arreglo del AV del portapapeles). **363 tests OK**, cobertura **87 %**. Evidencia completa en `DECISIONES.md` §3g.

Cerrado en esta tanda:

2. **P0 1(b) — Facebook: la v2.6 no tenía código propio** (solo yt-dlp) **y yt-dlp no soporta fotos**: `Unsupported URL` en `photo.php`, `/photo/`, `share/p/`, álbum y perfil. Propuesta nueva abajo, **sin implementar**.
3. **P0 punto 2 — pruebas reales del motor**: foto de X (JPEG 2992×1640, 224.183 B), miniatura máxima de YouTube (1280×720; `hqdefault` 480×360 cuando el video no tiene `maxres`), música 320/128 (+0,3 % real vs estimado) y título de 532 caracteres saneado a 183, ruta de 232.
4. **Informe de licencias** — `docs/LICENCIAS_TERCEROS.md`. Nada bloquea distribuir; checklist: `LICENCIAS.txt` junto al `.exe` + enlace en "Acerca de".
5. **Mapa del backend** — `docs/BACKEND_ESTADO.md` (87 % de cobertura, 363 tests).
6. **Parte B B1–B6** — portapapeles real, barra conectada, Ajustes, Acerca de, peso real descargado y verificación (capturas a 4 tamaños, `.exe` recompilado, teclado real, contraste AA, tokens en vivo). De paso se arreglaron dos botones muertos de la Cola: "Quitar" (solo funcionaba en canceladas) y "Limpiar" (no tenía manejador ni método).
7. **B7 REPORTE FINAL** — entregado al cierre de esta tanda.
8. **Bug propio del portapapeles (encontrado por el soak, arreglado)**: `clipboard._texto_windows` usaba `ctypes.wstring_at(puntero, 64 K)`, que lee **exactamente** 64 K caracteres sin detenerse en el NUL: sobre un bloque real de 40 bytes eso es una **violación de acceso** (9 volcados en la corrida 2). Ahora pide `GlobalSize` y lee solo lo que entra en el bloque. Verificado con 600 lecturas reales y 0 volcados; 2 tests nuevos. **En otra máquina ese AV podría matar el proceso** y verse igual que "la app se cerró sola".

Pendiente de verdad (Fase 8 o cuando Maki lo pida):

- **Pruebas del motor**: TikTok real y YouTube 4K/8K (hacen falta los links).
- **Actualizar el runtime de WebView2** (Evergreen oficial) y repetir la corrida larga de 1(a). No se hace sin el OK de Maki porque cambia la máquina.
- **`LICENCIAS.txt` dentro del paquete**: texto de la GPLv3 + enlace a la fuente exacta de ffmpeg, y el enlace desde "Acerca de".
- **Historial**: `core/history.py` sigue siendo stub (es de su fase).
- **Ruido de yt-dlp**: sus errores salen por stderr (`Media #1 is not a video`); en el `.exe` no se ve, pero conviene silenciarlos.

## (0b) Fotos de Facebook — propuesta (20/10/2026, NO implementada)

Lo que hay hoy: `images._via_facebook` usa `FacebookIE` de yt-dlp, que solo entiende videos. Un link de foto termina en "Ese sitio todavía no lo soportamos".

Propuesta (función nueva, cuando Maki la apruebe):

1. Detectar los formatos de foto: `/photo/?fbid=`, `photo.php?fbid=`, `/photos/a.NNN/NNN/`, `share/p/` y álbum (`media/set`).
2. Pedir el HTML de la página con el mismo cliente HTTP endurecido que ya usa `images.py` (lista de hosts, sin IP privadas, sin redirecciones fuera de la lista, tope de tamaño y de tiempo).
3. Sacar `og:image` (y `og:image:width/height`); si es un álbum, recorrer las imágenes del JSON embebido con tope de N.
4. Descargar la variante grande de `scontent*.fbcdn.net` con la misma red segura y guardar como JPEG con el nombre del post.
5. Si la página pide sesión (muro/cookies), mensaje claro: "Esa foto necesita una sesión de Facebook; todavía no la podemos bajar".

Riesgo: Facebook cambia el HTML seguido y bloquea IPs sin sesión. No se promete que funcione siempre.

Nota sobre las sesiones (OpenCode v1→v2, 18/10/2026): las conversaciones grandes siguen en la base (`ses_ed106da3…` 12–16/10 con 2196 mensajes, `ses_eb978978…` desde el 16/10 con 702, `ses_eefdeebf…` 06–10/10 con 1180, `ses_efa96459…` 04–05/10 con 716). Lo único que quedó fuera de la vista es contexto de chat, no trabajo: el repo y los commits están intactos.

## (a) Desvíos aprobados por Maki (frente a la imagen de referencia)

| Desvío | Detalle | Origen |
|---|---|---|
| Calidad con segmentados, no chips gigantes | Ver reglas de calidad en DECISIONES.md §5b (cambio aprobado por Maki 14/10/2026). | Fase 2D.2 (cerró la discusión de 2D) |
| Selector de tipo en card 3 | "Video / Música / Imagen" queda en la card 3 (en la referencia no existe). | Fase 2D, Parte 0d |
| Botón "Pegar" como ícono discreto en el campo | Card 1 tiene "Analizar" y "MIAUK!" como botones, y "Pegar del portapapeles" como ícono dentro del campo (junto a la ×). MIAUK! es el único botón de descarga. | Fase 2D.1 |
| Sin botón "Descargar" en card 3 | Quitado. MIAUK! es el único botón de descarga. | Fase 2D, Parte 0a |
| Texto de ayuda de card 1 | "cada click en MIAUK! agrega una descarga a la cola". Texto de Maki literal. | Fase 2D, Parte 0a |
| Banner recortado al contenido visible | `tools/crop_banner.py` deriva "Banner neón de Miauki recortado.png" (2158×421); el original queda intacto. | Fase 2D.1 |
| Banner: queda como está | Centrado y grande, sin ocupar todo el ancho. Banner modular DESCARTADO (no analizar ni proponer partirlo). | Fase 2D.2, cambio aprobado por Maki |
| Sin tarjeta de marca en la barra lateral | Quitada (repite el banner); el espacio se redistribuye con los mismos tokens. | Fase 2D.2, cambio aprobado por Maki |
| Sin lista de sitios en la columna derecha | Quitada (repite los íconos del banner); va el panel "Guardar en" + subtítulos (implementado en 2D.3). | Fase 2D.2/2D.3, cambio aprobado por Maki |
| Frase de la columna: "100% amigable", no "100% gratis" | La referencia dice "100% gratis"; la app usa "100% amigable" (decisión de fases anteriores). | Fase 2D |
| Aviso de la barra inferior: "Wow... un link: ¿Lo usamos?" | La referencia dice "Detecta un link"; la spec manda y se mantiene "Wow..." (decisión cerrada por Maki en 2D.3). | Fase 2D / 2D.3 |
| Título de la tarjeta 2 en 1 línea con tooltip | Decisión Maki 15/10 (a): 1 línea + "…" + título completo en `title`. | Fase 3B |
| Estado inicial sin datos de maqueta | Con el motor conectado el .exe nacía con link demo y "Me at the zoo"; ahora nace vacío (input, tarjeta 2, ruta real). | Fase 3B |

## (b) Pendientes de pulido (NO hacer hasta que Maki lo diga)

- ~~**Botón "MIAUK!" habilitado pero sin acción**~~: RESUELTO en Fase 4 Parte B — encola y descarga de verdad (cola, pausa, cancelar, reanudar; ventana real + .exe).
- ~~**Botón "Pegar del portapapeles" sin acción**~~: RESUELTO en Fase 5 Parte B — trae el link real del portapapeles (`core/clipboard.py`), lo pone en el campo y cierra la barra de aviso.
- ~~**Botón "Miauk" de la barra de portapapeles sin acción asignada**~~: RESUELTO en Fase 5 Parte B — hace lo que dice la spec §4: pone el link en el campo y **analiza** (no descarga).
- **Barra de portapapeles visible: Inicio gana un poco de scroll** (medido 20/10/2026): la barra ocupa alto real, así que mientras se ve el aviso "Wow... un link" la pantalla de Inicio pasa de 0 a **19–23 px de desborde a 1200×720** y **41–45 px a 1355×721** (con el aviso oculto vuelve a 0). Se arregla si Maki quiere que la barra **flote** sobre el contenido en vez de empujarlo; no se toca ahora porque cambia el alto reservado y el cierre de la Fase 5 ya está medido.
- **Frase de cierre de la columna** ("Tu video, en tus manos ♡") entra en 1 línea; la referencia la parte en 2. Detalle menor, resuelto si se pide pulir.
- **Widget "Detecta audio" / zona de audio**: fuera de alcance hasta su fase.
- **Aviso de "Descarga en curso"**: pertenece a la Fase 5; no se toca hasta entonces.
- **WebView2 Runtime (punto 7 de la Parte 0)**: **ya resuelto y documentado** — el .exe NO lo empaqueta: lo detecta por registro (`{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`, HKLM WOW6432Node + HKCU), y si falta baja el **Evergreen Bootstrapper oficial** (`MicrosoftEdgeWebview2Setup.exe`, ~1,9 MB, host `*.microsoft.com`/`*.dl.delivery.mp.microsoft.com` con HTTPS y URL final tras redirección), verifica la **firma Authenticode** con WinVerifyTrust, lo ejecuta `/silent /install` (shell=False, timeout 600 s), re-detecta y borra el descargado; sin internet o firma inválida → mensaje en español + MessageBoxW. Detalle y escenarios en DECISIONES.md §2b. **Lo único que falta** es la prueba real en una PC **sin** WebView2 instalado (Fase 8), porque en esta PC el Runtime ya está.

### Pulido visual (fase aparte, punto 9 de la Parte 0)

Cosmético/de acabado: NO es bug y NO se toca en la Fase 5. Cada punto se decide y se implementa en su propia fase de pulido (2F/7):

- Colores e íconos de cada estado de la Cola (hoy el color lo da `data-estado`, revisar contraste y que los íconos distingan estados de un vistazo).
- Título "Cola de Descargas" con la fuente manuscrita (Caveat) como en la referencia.
- Barra de progreso: que "procesando" no quede llena al 100 % de forma confusa (hoy sale al 100 %, decisión de Maki 17/10/2026: está bien así por ahora); evaluar barra indeterminada.
- "Guardar en": mostrar la ruta **completa** en el tooltip/`title` (hoy se abrevia por el medio en la columna).
- Verde del aviso "Agregada a la cola" más suave (hoy usa `--exito` pleno).
- Barra de scroll sin flechas (estilo propio) en la Cola y en la columna derecha.
- La frase de cierre de la columna ("Tu video, en tus manos ♡") y el lema derecho entran justos a 1200 px (la columna derecha muestra su scroll interno).
- A la ventana **mínima** (880×560) Inicio mantiene ~147 px de scroll central: se cierra solo si se decide ocultar el banner o la frase lateral a alturas bajas (ver (b), punto del scroll).
- **Alturas bajas: quedan 1 px de scroll central a 618 de alto** (antes 15): los recortes de la 3B (gap tarjeta 4→2, padding 12→8, pisos al contenido) pueden haberlo cerrado; verificar al retomar.
- **A 560 de alto quedan 59 px de scroll central** (antes 73): la ayuda ya se oculta y queda como descripción accesible del MIAUK. La tarjeta 1 (140 px) es lo que ata; no se toca hasta que Maki decida.
- **1161×618 sigue con 48 px de scroll central** (antes 64): límite conocido del diseño a esa ventana chica.
- **Ventana por defecto del .exe (1200×720): scroll central RESUELTO el 16/10/2026 (F4 Parte 0)**: era 23 px → **0 medido** en 1200×720, 1355×721 y 1600×900 (recortes mínimos: separación central 8→4, pisos de tarjeta vacía 150/148→144/142, relleno de tarjeta 8→6; banner y ventana intactos). "Más opciones" queda a medio ver bajo el corte con la ventana chica (Video/Música/Imagen y Mejor/Equilibrada/Liviana sí se ven).
- **Selector de tipo "Imagen" en vivo**: solo se probó con foto de Facebook (da el mensaje "Las fotos de Facebook todavía no se pueden analizar."); **falta probar con fotos reales de X** (lo pasa Maki).
- **Link de TikTok de un video real**: falta probar el analizador y la descarga con TikTok (link real lo pasa Maki).
- **Link de YouTube 4K/8K**: para comparar formatos con y sin runtime de JavaScript (link real lo pasa Maki; ver A8 en (c)).
- **Fotos de Facebook — investigación 0.2 (16/10/2026)**: se ejecutó la lógica de la v2.6 (`engine.probe` aislada) contra links reales: **la v2.6 tampoco resolvía fotos** — `photo/?fbid=` y `photo.php?fbid=` → "Unsupported URL"; `share/p/` y álbum `media/set` → "Unsupported URL"; `permalink.php?fbid=` → "Cannot parse data" del extractor; `share/r/` (reel) → OK porque es video, extractor Facebook de yt-dlp. O sea: la v1.0 no perdió nada vs la v2.6. **Propuesta (sin implementar, espera OK de Maki)**: vía propia que, con las cookies del navegador elegido en Ajustes, abra la página de la foto y extraiga la imagen grande (`og:image` / fbcdn) con la misma red segura de `images.py` (https, lista blanca, IP pública, límites, firma). Prioridad MEDIA; alternativa: mantener el mensaje amable actual.
- **Calidades extendidas (1440p/2160p en "Más opciones")**: implementadas y con test de contrato, pero el video de prueba en vivo solo tiene mp4 hasta 1080p.
- **Subtítulos: un solo .srt (16/10/2026, F4 4C P0.6b)**: `downloader._elegir_subs` preferí el idioma de los ajustes; si no está, el otro (es/en); si ninguno existe, no baja nada (sin fallar la descarga principal). Manuales antes que automáticos. Verificado en real: video con solo `en` disponible → baja `Me at the zoo.en.srt` (1 archivo).
- **No sobrescribir (16/10/2026, P0.6a)**: `validacion.nombre_base_libre` elige el nombre antes de bajar ("titulo", "titulo (2)"…) considerando todas las extensiones; probado con descargas reales repetidas (video `(2)`/`(3)`, música `mp3 (2)`). Antes la segunda descarga pisaba la primera (pérdida de datos).
- **Nombres de Windows (P0.6c)**: `validacion.sanear_nombre` quita `\ / : * ? " < > |`, saca punto/espacio final, despega reservados (`CON`→`CON_`) y recorta por el largo TOTAL de la ruta (`MAX_RUTA=240`). Cubierto con tests (no solo el título de 100).
- **Descarga duplicada de video**: verificada en real el 16/10/2026 (dos veces el mismo link → `Me at the zoo.mp4` + `Me at the zoo (2).mp4`, ambos intactos).

## (c) Decisiones de Maki (cerradas y aplicadas / abiertas)

Cerradas (15/10/2026, DECISIONES.md §3):
- **Fotos de Facebook**: mensaje "Las fotos de Facebook todavía no se pueden analizar." — VERIFICADO en ventana real y .exe.
- **A8 runtime JS de YouTube**: dejar como está; prioridad ALTA en este archivo.
- **Videos verticales**: etiqueta por el lado corto ("1080p") — implementado en `analyzer._altura`.
- **Scroll de la ventana por defecto**: atacar en orden (a) título 1 línea, (b) menos separación, (c) menos margen; banner y ventana intactos. APLICADO: 49→23 px.
- **Pantallas ≤640 px**: separador 12→8 ya estaba; ahora hereda además los recortes 3B.

Cerradas (16/10/2026, F4 4C P0.7 — seguridad del borde):
- **Snapshot del encolado validado (nuevo `miauki/core/validacion.py`)**: solo claves permitidas (`url_canonica, tipo, selector, contenedor, kbps, titulo, miniatura, con_subs, resolucion`); las desconocidas se descartan (la interfaz no puede colar `outtmpl`, rutas ni opciones de yt-dlp). Selector con charset acotado (`[A-Za-z0-9_.,+\-\[\]=<>^/()]`, admite filtros de yt-dlp), contenedor/kbps contra listas cerradas, `resolucion` entero 1..100000, miniatura solo `data:image/` con tope ~3 MB, url solo http/https.
- **Rutas acotadas**: `abrir_carpeta` solo abre la carpeta de ajustes (o algo dentro) o la carpeta de un ítem de la cola; `mostrar_archivo` solo revela archivos de ítems de la cola (explorer `/select`, sin shell). `cambiar_carpeta` rechaza raíz de unidad, `Windows` y `Program Files`, y verifica que se pueda escribir. El descargador rechaza cualquier archivo final que caiga fuera de la carpeta elegida. 23 tests nuevos (277 en total, OK).

Abiertas:
- **A8 — Runtime JavaScript para YouTube (yt-dlp) — PRIORIDAD ALTA**: la doc oficial (2026.08.19) dice que `yt-dlp-ejs` es "required for full YouTube support" y que hace falta un runtime JS (deno/node/bun/quickjs; solo deno se activa por defecto); sin runtime, yt-dlp avisa: "YouTube extraction without a JS runtime has been deprecated, and some formats may be missing". En esta PC: node 26.3.1 SÍ está (no se activa solo), deno/bun/quickjs NO, y el paquete yt-dlp-ejs NO está instalado (existe en PyPI, 0.8.0). Prueba real con un video de YouTube: 43 formatos y mismas alturas en las 3 configs probadas (por defecto, con node, con node+ejs remoto). **Simulación de PC limpia (P0.9, 16/10/2026)**: análisis real con la carpeta de node FUERA del PATH del proceso (subproceso con PATH recortado, sin instalar/desinstalar): **mismo resultado idéntico** (24 formatos, alturas 240/144 en "Me at the zoo") y **el mismo aviso** que en esta PC — o sea, hoy node NO se usa igual (solo deno se activa por defecto), así que una PC limpia se comporta idéntico. Opciones SIN aplicar: (1) instalar `yt-dlp-ejs` + habilitar `js_runtimes={"node": {}}` en `analyzer._opciones_ajustes`; (2) dejar como está (decisión actual de Maki); (3) empaquetar deno/quickjs portable en el .exe. **Esperando de Maki un link de YouTube 4K/8K** para medir si el aviso (falta de runtime JS) recorta formatos altos de verdad; hasta hoy, todos los casos medidos dan los mismos formatos y alturas con o sin node.
- **Scroll de la ventana por defecto**: RESUELTO 16/10/2026 (F4 Parte 0): separación central 8→4, pisos 144/142, relleno 8→6. **Re-medido (17/10/2026, F5 Parte 0 punto 8, `p5_medir.py` sobre `.central`): 0 px en 1200×720, 1355×721 y 1600×900 en los 4 estados de Inicio (vacío, resultado, aviso, aviso+resultado).** Causa del scroll que reapareció al entrar la 4C: el `h1` sr-only es el 1er hijo de `.central`, así que `:nth-child(1/2/3)` corría los pisos de las tarjetas (card3 quedaba sin piso) → corregido a `:nth-of-type` en `layout.css`; y la fila de calidad envolvía por el botón "Más opciones" (necesitaba 760 px y había 743) → relleno del segmentado 16→12.
- **A la ventana MÍNIMA (880×560 outer = 864×521 útiles) Inicio mantiene scroll interno de ~147 px** (con el aviso, ~155): en 389 px de alto de `.central` no entran el banner (76) + 3 tarjetas. **Límite conocido del diseño a esa ventana chica** (mismo caso que 1161×618, 48 px); no es regresión de la 5 (la card3 ya envolvía a ese ancho). Se cierra solo si se decide ocultar el banner o la frase lateral a alturas bajas (pulido responsive, Fase 2F). La afirmación anterior de "0 px a 880×560" medía el scroll de `body`, no el de `.central`.
- **"Peso total descargado: —"**: el puente de progreso ya emite los datos (B5, evento `progreso`); falta verificar en la UI que la etiqueta los use.
- **Descarga real en FB y X (tabla B6, 16/10/2026)**: `tools/probar_descarga.py` → YouTube OK (240p mp4, 635.505 B), Instagram OK (reel 1080p mkv, 2.494.423 B). Facebook (`watch/?v=`) → error REAL de yt-dlp "Cannot parse data" (extractor pide sesión; ya conocido de Fase 0/2D: requiere cookies). X (tweet de prueba inexistente) → error REAL "No video could be found". Ambos salen con mensaje amable (`error_desconocido`); no se inventó nada. Pendiente probar con links REALES cuando Maki los pase (igual que fotos de X y TikTok).
- **Fix de bloqueo `.part` (3d.16)**: aplicado y verificado en vivo (pausa/cancelar con 2160p real: `.part` inmovel y borrable mientras pausado; cancelar-en-vuelo limpia; reanudar funciona). 254 tests OK.

Cerradas (16/10/2026, F4 4C P0.5 — Facebook sin IDs de formato):
- **Selectores por altura y códec con respaldos** (nunca IDs efímeros): `analyzer._selector_video`. Probado real con el reel/watch de Facebook: baja en mkv (AV1+AAC), contenedor real == prometido (7,43 MB real vs 7,36 MB estimado, 4,63 MB/s). La segunda descarga del mismo título salió `…(2).mkv` (no sobrescribe).
- **Reintento con reanálisis silencioso**: `downloader._extraer_con_respaldo` — ante `calidad_no_disponible` reanaliza (`forzar=True`, solo log) y reintenta 1 vez con un selector nuevo de la misma altura. Cubierto por `test_downloader.py::ReintentoFormato`.
- **`errors.py`**: `"cannot parse data"` → `requiere_sesion` (Facebook sin sesión; el mensaje menciona "Ajustes → Cookies").

## (d) Conexiones postergadas (se programan en fases posteriores)

- **Botón "MIAUK!"**: descarga real (Fase 4): saneado del nombre de archivo (quitar `\ / : * ? " < > |`), y las URLs de `imagenes[]` deben pasar por la lista blanca de hosts + IPs públicas de `images._leer` (A6) antes de descargar.
- **Botones "Cambiar" (carpeta) y "Abrir carpeta"** del panel "Guardar en": solo aspecto hasta la fase que conecte ajustes/descargas (3/6).
- **Barra de portapapeles (?portapapeles=1)**: demo de Fase 2D; el .exe nunca la muestra. Conectar el detector real en su fase.
- **Dónde se accede a "Guardar en" en pantallas chicas** (<1000 px, columna oculta): propuesta sin implementar — en Ajustes ya está la carpeta de descargas; se puede repetir el acceso directo ahí o mostrarlo en la barra inferior. Decidir en el pulido responsive (Fase 2F).
- **Reglas de seguridad de la revisión de cierre (Parte B)** — aplicar en su fase, no antes: (1) **Fase 5/6**: el texto de sitios/errores ya entra por textContent (aplicado en 3B para el análisis); mantener ese patrón. (2) **Fase 4**: saneado del nombre de archivo + lista blanca de imágenes (arriba). (3) **Antes de la Fase 9 (release)**: correr una auditoría de dependencias (p.ej. `pip-audit` sobre `requirements.txt` fijado). Nota de diseño: yt-dlp analiza cualquier URL http/https sin lista blanca de dominios (spec §3, "lo demás pasa como 'otro'"), aceptado porque la app es de usuario único en desktop; las rutas sorprendentes (miniaturas, vías de imágenes) sí tienen lista blanca + IPs verificadas + sin redirects ciegos (A6). El TOCTOU de DNS (re-resuelve al conectar) queda como límite conocido de urllib.

## (e) Fase 5C - pendientes nuevos (20/10/2026)

- **`ProcessFailed` de WebView2 (A1) - Fase 8**: pywebview 6.2.1 no lo expone. Se probó
  engancharlo desde `loaded` accediendo a `CoreWebView2` y **congela la interfaz** (la
  ventana no responde a WM_CLOSE; probado en ventana real: con el enganche no cierra,
  sin él cierra con código 0). Hoy solo se registra que no se puede enganchar. Para
  Fase 8: buscar una vía que no toque el hilo de la UI (por ejemplo, un proceso aparte
  que lea el estado de los `msedgewebview2.exe` del Job Object, o esperar a que
  pywebview exponga el evento).
- **Barra del portapapeles a 880x560 (A3)**: no tapa ningún control, pero se superpone
  al banner decorativo (logo). Si molesta, en Fase 8 implementar el reemplazo por el
  texto de ayuda con altura reservada (la spec ya lo contempla).
- **A8 - runtime JS de YouTube**: probado el 20/10/2026 con el 4K `x91MPoITQ3I`
  ("SAMSUNG 4K DEMO QLED"): 37 formatos de video, mismas alturas
  (2160/1440/1080/720/480/360/240/144) y mismos códecs **con y sin `node`** como
  runtime (`js_runtimes={"node": {}}`). El aviso de yt-dlp aparece igual, pero **no
  recorta formatos en este caso**. Se mantiene la decisión de Maki: dejar como está
  (sin instalar deno ni `yt-dlp-ejs`) y revisar si aparece un video donde falte un
  formato.
- **Instalador, firma de código y prueba en Windows 10 limpio**: ver
  `docs/DISTRIBUCION.md` (propuesta y costos verificados).
- **Recuperación "recargar + cola_actual()" (A1) - Fase 8**: no se implementó porque
  las dos vías posibles quedan tapadas: `closed` llega cuando la ventana ya está
  destruida (no hay dónde recargar) y `ProcessFailed` congela la UI (ver el punto
  anterior). Lo que sí queda cubierto: al volver a abrir, la app refresca el estado de
  la cola desde `cola.json` + `cola_actual()`, y lo que quedó a medias aparece como
  "Interrumpida". Si en Fase 8 se consigue escuchar `ProcessFailed` sin bloquear, la
  recarga es una línea (`ventana.evaluate_js("location.reload()")`).

## (f) Fase 7 - cerrada el 20/10/2026

Todo lo de la tanda quedo hecho y probado (detalle y numeros en DECISIONES §3j-§3r):

- ~~**0.1**~~ carpeta de datos redirigible (`MIAUKI_DATOS`), guardia de dos capas
  y copia de seguridad de historial/cola/ajustes. Historial y cola reales vacios.
- ~~**0.2**~~ el Historial ya no muestra "otro": guarda el sitio derivado del link.
- ~~**0.3**~~ TikTok probado y documentado (§3k).
- ~~**A**~~ actualizador propio de yt-dlp (`docs/ACTUALIZADOR.md`), tarjeta en
  Ajustes, prueba real con el `.exe`.
- ~~**B1**~~ maxima compatibilidad H.264/AAC hasta 1080p + aviso de formato.
- ~~**B2**~~ Ctrl+V y arrastrar y soltar con validacion en el puente.
- ~~**B3**~~ parpadeo en la barra de tareas al terminar (ventana de atras).
- ~~**C**~~ recorrido guiado de 7 pasos, una sola vez y repetible desde Acerca.
- ~~**D1-D5b**~~ pulido visual y textos propuestos para la jerga (§3q).
- ~~**E**~~ `.exe` medido y optimizado (84,0 MB), `docs/PRUEBA_EXE.md` y paquete
  para Windows 10 armado fuera del repo.

### Pendientes que salen de la Fase 7

- **Probar el `.exe` en un Windows 10 limpio**: la guia esta (`docs/PRUEBA_EXE.md`,
  12 puntos) y el zip tambien (`%TEMP%\opencode\entrega\`), pero Maki todavia no
  lo abrio en la maquina limpia.
- **Aprobar los textos de jerga** propuestos en §3q (tabla de 10 filas).
- **`yt-dlp-ejs`**: el motor moderno de YouTube lo pide para algunos formatos.
  Hoy no se incluye; si aparecen videos que fallan, es el primer sospechoso.
  final del proyecto.

 PENDIENTES — Miauki YT v1.0

Actualizado: 22/10/2026 (Fase 9 Parte B cerrada; ver §3w de DECISIONES y la sección (g) al final para lo que queda).
Se actualiza en cada fase. Fuentes: especificación de cada fase + decisiones de Maki.

## (0) Fase 5 — trabajo pendiente (guardado 19/10/2026; **cerrado el 20/10/2026**)

Estado del repo: limpio. Commits de la tanda: `d4cd8e2` (coma decimal), `9c958c1` (pulido de Inicio), `41430b7` (foco/progreso de la Cola), `25fab9c` (decisiones §3f), B1 (portapapeles), `41146b6` (B2 barra), `f3a25fc` (B3/B4/B5 + "Quitar" y "Limpiar"), `4fd2e6f` (la barra analiza), `f82c860` (backend al día) y `8e778d5` (arreglo del AV del portapapeles). **363 tests OK**, cobertura **87 %**. Evidencia completa en `DECISIONES.md` §3g.

Cerrado en esta tanda:

2. **P0 1(b) — Facebook: la v2.6 no tenía código propio** (solo yt-dlp) **y yt-dlp no soporta fotos**: `Unsupported URL` en `photo.php`, `/photo/`, `share/p/`, álbum y perfil. Propuesta nueva abajo, **sin implementar**.
3. **P0 punto 2 — pruebas reales del motor**: foto de X (JPEG 2992×1640, 224.183 B), miniatura máxima de YouTube (1280×720; `hqdefault` 480×360 cuando el video no tiene `maxres`), música 320/128 (+0,3 % real vs estimado) y título de 532 caracteres saneado a 183, ruta de 232.
4. **Informe de licencias** — `docs/LICENCIAS_TERCEROS.md`. Nada bloquea distribuir; checklist: `LICENCIAS.txt` junto al `.exe` + enlace en "Acerca de".
5. **Mapa del backend** — `docs/BACKEND_ESTADO.md` (87 % de cobertura, 363 tests).
6. **Parte B B1–B6** — portapapeles real, barra conectada, Ajustes, Acerca de, peso real descargado y verificación (capturas a 4 tamaños, `.exe` recompilado, teclado real, contraste AA, tokens en vivo). De paso se arreglaron dos botones muertos de la Cola: "Quitar" (solo funcionaba en canceladas) y "Limpiar" (no tenía manejador ni método).
7. **B7 REPORTE FINAL** — entregado al cierre de esta tanda.
8. **Bug propio del portapapeles (encontrado por el soak, arreglado)**: `clipboard._texto_windows` usaba `ctypes.wstring_at(puntero, 64 K)`, que lee **exactamente** 64 K caracteres sin detenerse en el NUL: sobre un bloque real de 40 bytes eso es una **violación de acceso** (9 volcados en la corrida 2). Ahora pide `GlobalSize` y lee solo lo que entra en el bloque. Verificado con 600 lecturas reales y 0 volcados; 2 tests nuevos. **En otra máquina ese AV podría matar el proceso** y verse igual que "la app se cerró sola".

Pendiente de verdad (Fase 8 o cuando Maki lo pida):

- **Pruebas del motor**: TikTok real y YouTube 4K/8K (hacen falta los links).
- **Actualizar el runtime de WebView2** (Evergreen oficial) y repetir la corrida larga de 1(a). No se hace sin el OK de Maki porque cambia la máquina.
- **`LICENCIAS.txt` dentro del paquete**: texto de la GPLv3 + enlace a la fuente exacta de ffmpeg, y el enlace desde "Acerca de".
- **Historial**: `core/history.py` sigue siendo stub (es de su fase).
- **Ruido de yt-dlp**: sus errores salen por stderr (`Media #1 is not a video`); en el `.exe` no se ve, pero conviene silenciarlos.

## (0b) Fotos de Facebook — propuesta (20/10/2026, NO implementada)

Lo que hay hoy: `images._via_facebook` usa `FacebookIE` de yt-dlp, que solo entiende videos. Un link de foto termina en "Ese sitio todavía no lo soportamos".

Propuesta (función nueva, cuando Maki la apruebe):

1. Detectar los formatos de foto: `/photo/?fbid=`, `photo.php?fbid=`, `/photos/a.NNN/NNN/`, `share/p/` y álbum (`media/set`).
2. Pedir el HTML de la página con el mismo cliente HTTP endurecido que ya usa `images.py` (lista de hosts, sin IP privadas, sin redirecciones fuera de la lista, tope de tamaño y de tiempo).
3. Sacar `og:image` (y `og:image:width/height`); si es un álbum, recorrer las imágenes del JSON embebido con tope de N.
4. Descargar la variante grande de `scontent*.fbcdn.net` con la misma red segura y guardar como JPEG con el nombre del post.
5. Si la página pide sesión (muro/cookies), mensaje claro: "Esa foto necesita una sesión de Facebook; todavía no la podemos bajar".

Riesgo: Facebook cambia el HTML seguido y bloquea IPs sin sesión. No se promete que funcione siempre.

Nota sobre las sesiones (OpenCode v1→v2, 18/10/2026): las conversaciones grandes siguen en la base (`ses_ed106da3…` 12–16/10 con 2196 mensajes, `ses_eb978978…` desde el 16/10 con 702, `ses_eefdeebf…` 06–10/10 con 1180, `ses_efa96459…` 04–05/10 con 716). Lo único que quedó fuera de la vista es contexto de chat, no trabajo: el repo y los commits están intactos.

## (a) Desvíos aprobados por Maki (frente a la imagen de referencia)

| Desvío | Detalle | Origen |
|---|---|---|
| Calidad con segmentados, no chips gigantes | Ver reglas de calidad en DECISIONES.md §5b (cambio aprobado por Maki 14/10/2026). | Fase 2D.2 (cerró la discusión de 2D) |
| Selector de tipo en card 3 | "Video / Música / Imagen" queda en la card 3 (en la referencia no existe). | Fase 2D, Parte 0d |
| Botón "Pegar" como ícono discreto en el campo | Card 1 tiene "Analizar" y "MIAUK!" como botones, y "Pegar del portapapeles" como ícono dentro del campo (junto a la ×). MIAUK! es el único botón de descarga. | Fase 2D.1 |
| Sin botón "Descargar" en card 3 | Quitado. MIAUK! es el único botón de descarga. | Fase 2D, Parte 0a |
| Texto de ayuda de card 1 | "cada click en MIAUK! agrega una descarga a la cola". Texto de Maki literal. | Fase 2D, Parte 0a |
| Banner recortado al contenido visible | `tools/crop_banner.py` deriva "Banner neón de Miauki recortado.png" (2158×421); el original queda intacto. | Fase 2D.1 |
| Banner: queda como está | Centrado y grande, sin ocupar todo el ancho. Banner modular DESCARTADO (no analizar ni proponer partirlo). | Fase 2D.2, cambio aprobado por Maki |
| Sin tarjeta de marca en la barra lateral | Quitada (repite el banner); el espacio se redistribuye con los mismos tokens. | Fase 2D.2, cambio aprobado por Maki |
| Sin lista de sitios en la columna derecha | Quitada (repite los íconos del banner); va el panel "Guardar en" + subtítulos (implementado en 2D.3). | Fase 2D.2/2D.3, cambio aprobado por Maki |
| Frase de la columna: "100% amigable", no "100% gratis" | La referencia dice "100% gratis"; la app usa "100% amigable" (decisión de fases anteriores). | Fase 2D |
| Aviso de la barra inferior: "Wow... un link: ¿Lo usamos?" | La referencia dice "Detecta un link"; la spec manda y se mantiene "Wow..." (decisión cerrada por Maki en 2D.3). | Fase 2D / 2D.3 |
| Título de la tarjeta 2 en 1 línea con tooltip | Decisión Maki 15/10 (a): 1 línea + "…" + título completo en `title`. | Fase 3B |
| Estado inicial sin datos de maqueta | Con el motor conectado el .exe nacía con link demo y "Me at the zoo"; ahora nace vacío (input, tarjeta 2, ruta real). | Fase 3B |

## (b) Pendientes de pulido (NO hacer hasta que Maki lo diga)

- ~~**Botón "MIAUK!" habilitado pero sin acción**~~: RESUELTO en Fase 4 Parte B — encola y descarga de verdad (cola, pausa, cancelar, reanudar; ventana real + .exe).
- ~~**Botón "Pegar del portapapeles" sin acción**~~: RESUELTO en Fase 5 Parte B — trae el link real del portapapeles (`core/clipboard.py`), lo pone en el campo y cierra la barra de aviso.
- ~~**Botón "Miauk" de la barra de portapapeles sin acción asignada**~~: RESUELTO en Fase 5 Parte B — hace lo que dice la spec §4: pone el link en el campo y **analiza** (no descarga).
- **Barra de portapapeles visible: Inicio gana un poco de scroll** (medido 20/10/2026): la barra ocupa alto real, así que mientras se ve el aviso "Wow... un link" la pantalla de Inicio pasa de 0 a **19–23 px de desborde a 1200×720** y **41–45 px a 1355×721** (con el aviso oculto vuelve a 0). Se arregla si Maki quiere que la barra **flote** sobre el contenido en vez de empujarlo; no se toca ahora porque cambia el alto reservado y el cierre de la Fase 5 ya está medido.
- **Frase de cierre de la columna** ("Tu video, en tus manos ♡") entra en 1 línea; la referencia la parte en 2. Detalle menor, resuelto si se pide pulir.
- **Widget "Detecta audio" / zona de audio**: fuera de alcance hasta su fase.
- **Aviso de "Descarga en curso"**: pertenece a la Fase 5; no se toca hasta entonces.
- **WebView2 Runtime (punto 7 de la Parte 0)**: **ya resuelto y documentado** — el .exe NO lo empaqueta: lo detecta por registro (`{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`, HKLM WOW6432Node + HKCU), y si falta baja el **Evergreen Bootstrapper oficial** (`MicrosoftEdgeWebview2Setup.exe`, ~1,9 MB, host `*.microsoft.com`/`*.dl.delivery.mp.microsoft.com` con HTTPS y URL final tras redirección), verifica la **firma Authenticode** con WinVerifyTrust, lo ejecuta `/silent /install` (shell=False, timeout 600 s), re-detecta y borra el descargado; sin internet o firma inválida → mensaje en español + MessageBoxW. Detalle y escenarios en DECISIONES.md §2b. **Lo único que falta** es la prueba real en una PC **sin** WebView2 instalado (Fase 8), porque en esta PC el Runtime ya está.

### Pulido visual (fase aparte, punto 9 de la Parte 0)

Cosmético/de acabado: NO es bug y NO se toca en la Fase 5. Cada punto se decide y se implementa en su propia fase de pulido (2F/7):

- Colores e íconos de cada estado de la Cola (hoy el color lo da `data-estado`, revisar contraste y que los íconos distingan estados de un vistazo).
- Título "Cola de Descargas" con la fuente manuscrita (Caveat) como en la referencia.
- Barra de progreso: que "procesando" no quede llena al 100 % de forma confusa (hoy sale al 100 %, decisión de Maki 17/10/2026: está bien así por ahora); evaluar barra indeterminada.
- "Guardar en": mostrar la ruta **completa** en el tooltip/`title` (hoy se abrevia por el medio en la columna).
- Verde del aviso "Agregada a la cola" más suave (hoy usa `--exito` pleno).
- Barra de scroll sin flechas (estilo propio) en la Cola y en la columna derecha.
- La frase de cierre de la columna ("Tu video, en tus manos ♡") y el lema derecho entran justos a 1200 px (la columna derecha muestra su scroll interno).
- A la ventana **mínima** (880×560) Inicio mantiene ~147 px de scroll central: se cierra solo si se decide ocultar el banner o la frase lateral a alturas bajas (ver (b), punto del scroll).
- **Alturas bajas: quedan 1 px de scroll central a 618 de alto** (antes 15): los recortes de la 3B (gap tarjeta 4→2, padding 12→8, pisos al contenido) pueden haberlo cerrado; verificar al retomar.
- **A 560 de alto quedan 59 px de scroll central** (antes 73): la ayuda ya se oculta y queda como descripción accesible del MIAUK. La tarjeta 1 (140 px) es lo que ata; no se toca hasta que Maki decida.
- **1161×618 sigue con 48 px de scroll central** (antes 64): límite conocido del diseño a esa ventana chica.
- **Ventana por defecto del .exe (1200×720): scroll central RESUELTO el 16/10/2026 (F4 Parte 0)**: era 23 px → **0 medido** en 1200×720, 1355×721 y 1600×900 (recortes mínimos: separación central 8→4, pisos de tarjeta vacía 150/148→144/142, relleno de tarjeta 8→6; banner y ventana intactos). "Más opciones" queda a medio ver bajo el corte con la ventana chica (Video/Música/Imagen y Mejor/Equilibrada/Liviana sí se ven).
- **Selector de tipo "Imagen" en vivo**: solo se probó con foto de Facebook (da el mensaje "Las fotos de Facebook todavía no se pueden analizar."); **falta probar con fotos reales de X** (lo pasa Maki).
- **Link de TikTok de un video real**: falta probar el analizador y la descarga con TikTok (link real lo pasa Maki).
- **Link de YouTube 4K/8K**: para comparar formatos con y sin runtime de JavaScript (link real lo pasa Maki; ver A8 en (c)).
- **Fotos de Facebook — investigación 0.2 (16/10/2026)**: se ejecutó la lógica de la v2.6 (`engine.probe` aislada) contra links reales: **la v2.6 tampoco resolvía fotos** — `photo/?fbid=` y `photo.php?fbid=` → "Unsupported URL"; `share/p/` y álbum `media/set` → "Unsupported URL"; `permalink.php?fbid=` → "Cannot parse data" del extractor; `share/r/` (reel) → OK porque es video, extractor Facebook de yt-dlp. O sea: la v1.0 no perdió nada vs la v2.6. **Propuesta (sin implementar, espera OK de Maki)**: vía propia que, con las cookies del navegador elegido en Ajustes, abra la página de la foto y extraiga la imagen grande (`og:image` / fbcdn) con la misma red segura de `images.py` (https, lista blanca, IP pública, límites, firma). Prioridad MEDIA; alternativa: mantener el mensaje amable actual.
- **Calidades extendidas (1440p/2160p en "Más opciones")**: implementadas y con test de contrato, pero el video de prueba en vivo solo tiene mp4 hasta 1080p.
- **Subtítulos: un solo .srt (16/10/2026, F4 4C P0.6b)**: `downloader._elegir_subs` preferí el idioma de los ajustes; si no está, el otro (es/en); si ninguno existe, no baja nada (sin fallar la descarga principal). Manuales antes que automáticos. Verificado en real: video con solo `en` disponible → baja `Me at the zoo.en.srt` (1 archivo).
- **No sobrescribir (16/10/2026, P0.6a)**: `validacion.nombre_base_libre` elige el nombre antes de bajar ("titulo", "titulo (2)"…) considerando todas las extensiones; probado con descargas reales repetidas (video `(2)`/`(3)`, música `mp3 (2)`). Antes la segunda descarga pisaba la primera (pérdida de datos).
- **Nombres de Windows (P0.6c)**: `validacion.sanear_nombre` quita `\ / : * ? " < > |`, saca punto/espacio final, despega reservados (`CON`→`CON_`) y recorta por el largo TOTAL de la ruta (`MAX_RUTA=240`). Cubierto con tests (no solo el título de 100).
- **Descarga duplicada de video**: verificada en real el 16/10/2026 (dos veces el mismo link → `Me at the zoo.mp4` + `Me at the zoo (2).mp4`, ambos intactos).

## (c) Decisiones de Maki (cerradas y aplicadas / abiertas)

Cerradas (15/10/2026, DECISIONES.md §3):
- **Fotos de Facebook**: mensaje "Las fotos de Facebook todavía no se pueden analizar." — VERIFICADO en ventana real y .exe.
- **A8 runtime JS de YouTube**: dejar como está; prioridad ALTA en este archivo.
- **Videos verticales**: etiqueta por el lado corto ("1080p") — implementado en `analyzer._altura`.
- **Scroll de la ventana por defecto**: atacar en orden (a) título 1 línea, (b) menos separación, (c) menos margen; banner y ventana intactos. APLICADO: 49→23 px.
- **Pantallas ≤640 px**: separador 12→8 ya estaba; ahora hereda además los recortes 3B.

Cerradas (16/10/2026, F4 4C P0.7 — seguridad del borde):
- **Snapshot del encolado validado (nuevo `miauki/core/validacion.py`)**: solo claves permitidas (`url_canonica, tipo, selector, contenedor, kbps, titulo, miniatura, con_subs, resolucion`); las desconocidas se descartan (la interfaz no puede colar `outtmpl`, rutas ni opciones de yt-dlp). Selector con charset acotado (`[A-Za-z0-9_.,+\-\[\]=<>^/()]`, admite filtros de yt-dlp), contenedor/kbps contra listas cerradas, `resolucion` entero 1..100000, miniatura solo `data:image/` con tope ~3 MB, url solo http/https.
- **Rutas acotadas**: `abrir_carpeta` solo abre la carpeta de ajustes (o algo dentro) o la carpeta de un ítem de la cola; `mostrar_archivo` solo revela archivos de ítems de la cola (explorer `/select`, sin shell). `cambiar_carpeta` rechaza raíz de unidad, `Windows` y `Program Files`, y verifica que se pueda escribir. El descargador rechaza cualquier archivo final que caiga fuera de la carpeta elegida. 23 tests nuevos (277 en total, OK).

Abiertas:
- **A8 — Runtime JavaScript para YouTube (yt-dlp) — PRIORIDAD ALTA**: la doc oficial (2026.08.19) dice que `yt-dlp-ejs` es "required for full YouTube support" y que hace falta un runtime JS (deno/node/bun/quickjs; solo deno se activa por defecto); sin runtime, yt-dlp avisa: "YouTube extraction without a JS runtime has been deprecated, and some formats may be missing". En esta PC: node 26.3.1 SÍ está (no se activa solo), deno/bun/quickjs NO, y el paquete yt-dlp-ejs NO está instalado (existe en PyPI, 0.8.0). Prueba real con un video de YouTube: 43 formatos y mismas alturas en las 3 configs probadas (por defecto, con node, con node+ejs remoto). **Simulación de PC limpia (P0.9, 16/10/2026)**: análisis real con la carpeta de node FUERA del PATH del proceso (subproceso con PATH recortado, sin instalar/desinstalar): **mismo resultado idéntico** (24 formatos, alturas 240/144 en "Me at the zoo") y **el mismo aviso** que en esta PC — o sea, hoy node NO se usa igual (solo deno se activa por defecto), así que una PC limpia se comporta idéntico. Opciones SIN aplicar: (1) instalar `yt-dlp-ejs` + habilitar `js_runtimes={"node": {}}` en `analyzer._opciones_ajustes`; (2) dejar como está (decisión actual de Maki); (3) empaquetar deno/quickjs portable en el .exe. **Esperando de Maki un link de YouTube 4K/8K** para medir si el aviso (falta de runtime JS) recorta formatos altos de verdad; hasta hoy, todos los casos medidos dan los mismos formatos y alturas con o sin node.
- **Scroll de la ventana por defecto**: RESUELTO 16/10/2026 (F4 Parte 0): separación central 8→4, pisos 144/142, relleno 8→6. **Re-medido (17/10/2026, F5 Parte 0 punto 8, `p5_medir.py` sobre `.central`): 0 px en 1200×720, 1355×721 y 1600×900 en los 4 estados de Inicio (vacío, resultado, aviso, aviso+resultado).** Causa del scroll que reapareció al entrar la 4C: el `h1` sr-only es el 1er hijo de `.central`, así que `:nth-child(1/2/3)` corría los pisos de las tarjetas (card3 quedaba sin piso) → corregido a `:nth-of-type` en `layout.css`; y la fila de calidad envolvía por el botón "Más opciones" (necesitaba 760 px y había 743) → relleno del segmentado 16→12.
- **A la ventana MÍNIMA (880×560 outer = 864×521 útiles) Inicio mantiene scroll interno de ~147 px** (con el aviso, ~155): en 389 px de alto de `.central` no entran el banner (76) + 3 tarjetas. **Límite conocido del diseño a esa ventana chica** (mismo caso que 1161×618, 48 px); no es regresión de la 5 (la card3 ya envolvía a ese ancho). Se cierra solo si se decide ocultar el banner o la frase lateral a alturas bajas (pulido responsive, Fase 2F). La afirmación anterior de "0 px a 880×560" medía el scroll de `body`, no el de `.central`.
- **"Peso total descargado: —"**: el puente de progreso ya emite los datos (B5, evento `progreso`); falta verificar en la UI que la etiqueta los use.
- **Descarga real en FB y X (tabla B6, 16/10/2026)**: `tools/probar_descarga.py` → YouTube OK (240p mp4, 635.505 B), Instagram OK (reel 1080p mkv, 2.494.423 B). Facebook (`watch/?v=`) → error REAL de yt-dlp "Cannot parse data" (extractor pide sesión; ya conocido de Fase 0/2D: requiere cookies). X (tweet de prueba inexistente) → error REAL "No video could be found". Ambos salen con mensaje amable (`error_desconocido`); no se inventó nada. Pendiente probar con links REALES cuando Maki los pase (igual que fotos de X y TikTok).
- **Fix de bloqueo `.part` (3d.16)**: aplicado y verificado en vivo (pausa/cancelar con 2160p real: `.part` inmovel y borrable mientras pausado; cancelar-en-vuelo limpia; reanudar funciona). 254 tests OK.

Cerradas (16/10/2026, F4 4C P0.5 — Facebook sin IDs de formato):
- **Selectores por altura y códec con respaldos** (nunca IDs efímeros): `analyzer._selector_video`. Probado real con el reel/watch de Facebook: baja en mkv (AV1+AAC), contenedor real == prometido (7,43 MB real vs 7,36 MB estimado, 4,63 MB/s). La segunda descarga del mismo título salió `…(2).mkv` (no sobrescribe).
- **Reintento con reanálisis silencioso**: `downloader._extraer_con_respaldo` — ante `calidad_no_disponible` reanaliza (`forzar=True`, solo log) y reintenta 1 vez con un selector nuevo de la misma altura. Cubierto por `test_downloader.py::ReintentoFormato`.
- **`errors.py`**: `"cannot parse data"` → `requiere_sesion` (Facebook sin sesión; el mensaje menciona "Ajustes → Cookies").

## (d) Conexiones postergadas (se programan en fases posteriores)

- **Botón "MIAUK!"**: descarga real (Fase 4): saneado del nombre de archivo (quitar `\ / : * ? " < > |`), y las URLs de `imagenes[]` deben pasar por la lista blanca de hosts + IPs públicas de `images._leer` (A6) antes de descargar.
- **Botones "Cambiar" (carpeta) y "Abrir carpeta"** del panel "Guardar en": solo aspecto hasta la fase que conecte ajustes/descargas (3/6).
- **Barra de portapapeles (?portapapeles=1)**: demo de Fase 2D; el .exe nunca la muestra. Conectar el detector real en su fase.
- **Dónde se accede a "Guardar en" en pantallas chicas** (<1000 px, columna oculta): propuesta sin implementar — en Ajustes ya está la carpeta de descargas; se puede repetir el acceso directo ahí o mostrarlo en la barra inferior. Decidir en el pulido responsive (Fase 2F).
- **Reglas de seguridad de la revisión de cierre (Parte B)** — aplicar en su fase, no antes: (1) **Fase 5/6**: el texto de sitios/errores ya entra por textContent (aplicado en 3B para el análisis); mantener ese patrón. (2) **Fase 4**: saneado del nombre de archivo + lista blanca de imágenes (arriba). (3) **Antes de la Fase 9 (release)**: correr una auditoría de dependencias (p.ej. `pip-audit` sobre `requirements.txt` fijado). Nota de diseño: yt-dlp analiza cualquier URL http/https sin lista blanca de dominios (spec §3, "lo demás pasa como 'otro'"), aceptado porque la app es de usuario único en desktop; las rutas sorprendentes (miniaturas, vías de imágenes) sí tienen lista blanca + IPs verificadas + sin redirects ciegos (A6). El TOCTOU de DNS (re-resuelve al conectar) queda como límite conocido de urllib.

## (e) Fase 5C - pendientes nuevos (20/10/2026)

- **`ProcessFailed` de WebView2 (A1) - Fase 8**: pywebview 6.2.1 no lo expone. Se probó
  engancharlo desde `loaded` accediendo a `CoreWebView2` y **congela la interfaz** (la
  ventana no responde a WM_CLOSE; probado en ventana real: con el enganche no cierra,
  sin él cierra con código 0). Hoy solo se registra que no se puede enganchar. Para
  Fase 8: buscar una vía que no toque el hilo de la UI (por ejemplo, un proceso aparte
  que lea el estado de los `msedgewebview2.exe` del Job Object, o esperar a que
  pywebview exponga el evento).
- **Barra del portapapeles a 880x560 (A3)**: no tapa ningún control, pero se superpone
  al banner decorativo (logo). Si molesta, en Fase 8 implementar el reemplazo por el
  texto de ayuda con altura reservada (la spec ya lo contempla).
- **A8 - runtime JS de YouTube**: probado el 20/10/2026 con el 4K `x91MPoITQ3I`
  ("SAMSUNG 4K DEMO QLED"): 37 formatos de video, mismas alturas
  (2160/1440/1080/720/480/360/240/144) y mismos códecs **con y sin `node`** como
  runtime (`js_runtimes={"node": {}}`). El aviso de yt-dlp aparece igual, pero **no
  recorta formatos en este caso**. Se mantiene la decisión de Maki: dejar como está
  (sin instalar deno ni `yt-dlp-ejs`) y revisar si aparece un video donde falte un
  formato.
- **Instalador, firma de código y prueba en Windows 10 limpio**: ver
  `docs/DISTRIBUCION.md` (propuesta y costos verificados).
- **Recuperación "recargar + cola_actual()" (A1) - Fase 8**: no se implementó porque
  las dos vías posibles quedan tapadas: `closed` llega cuando la ventana ya está
  destruida (no hay dónde recargar) y `ProcessFailed` congela la UI (ver el punto
  anterior). Lo que sí queda cubierto: al volver a abrir, la app refresca el estado de
  la cola desde `cola.json` + `cola_actual()`, y lo que quedó a medias aparece como
  "Interrumpida". Si en Fase 8 se consigue escuchar `ProcessFailed` sin bloquear, la
  recarga es una línea (`ventana.evaluate_js("location.reload()")`).

## (f) Fase 7 - en curso (20/10/2026)

Trabajo de la tanda, en orden (se va tachando al cerrar cada parte):

- **0.1** Redirigir la carpeta de datos en pruebas y herramientas (variable de
  entorno `MIAUKI_DATOS`), test que falla si algo escribe en la carpeta real de
  Maki, y limpieza del historial/cola reales con copia de seguridad.
- **0.2** Historial mostrando "otro" como sitio en entradas de YouTube.
- ~~**0.3** TikTok~~ **cerrado 20/10/2026**: descarga real de 10 s en 1080p (1,68 MB)
  y 720p (0,89 MB), contenedor mp4, sin cookies. Ver §3k.
- **A** Actualizador de yt-dlp (diseño en `docs/ACTUALIZADOR.md`, motor propio con
  prueba de humo, reversa y UI en Ajustes).
- **B1** Máxima compatibilidad (H.264 + AAC hasta 1080p) y aviso de MKV/AV1.
- **B2** Arrastrar y soltar + Ctrl+V.
- **B3** Parpadeo en la barra de tareas al terminar.
- **C** Recorrido guiado "Así de fácil se usa".
- **D1-D5b** Pulido visual (tarjetas, Acerca, Historial, Cola, Ajustes, Inicio).
- **E** Medición del `.exe`, optimizaciones baratas y `docs/PRUEBA_EXE.md`.

El programa se distribuye **gratis** (decisión de Maki del 22/10/2026, §3v): no hay
demo ni licencia. La versión en inglés va al final del proyecto.

## (g) Fase 9 - Parte B: lo que queda (22/10/2026, actualizado 23/10/2026)

Hecho y probado: ver `DECISIONES.md` §3w y §3x. Acá solo lo que **no** está cerrado.

**Cerrado el 23/10/2026**: barra ×0,8 y origen abajo a la derecha; archivo de
cookies en Ajustes (B2b, ver `docs/COOKIES.md`); 0 px de scroll a 1355×721 con
3 fotos; la entrega verifica que el `.exe` tenga la interfaz del repo.

### Textos nuevos, esperando el OK de Maki

| Dónde | Texto |
|---|---|
| Card 3, cuando el post es solo imágenes | "Este post solo tiene imágenes: no hay video ni audio para elegir." |
| Botón del error | "Ir a Ajustes" |
| Aria del asa de la barra | "Mover el aviso de link (flechas del teclado)" |
| Error, navegador con cookies cifradas | "Ese navegador guarda las cookies cifradas y no podemos leerlas. Probá con Firefox, o elegí un archivo de cookies en Ajustes." |
| Error, navegador sin cookies | "No encontramos cookies de ese navegador. Entrá al sitio, iniciá sesión y probá de nuevo, o elegí un archivo de cookies en Ajustes." |
| Error, post que pide sesión en X | "Ese post no se puede ver sin iniciar sesión (puede ser para mayores o de una cuenta protegida). Activá «Usar el inicio de sesión de tu navegador» en Ajustes." |
| Ajustes, botón | "Elegir archivo…" |
| Ajustes, botón | "Quitar" |
| Ajustes, sin archivo | "Ningún archivo elegido." |
| Ajustes, con archivo | "Archivo: {nombre}" |
| Ajustes, aviso de privacidad | "El archivo da acceso a tu cuenta: no lo compartas ni lo subas a ningún lado. Se guarda solo la ruta, no una copia." |
| Error, archivo de cookies borrado | "El archivo de cookies ya no está en esa ruta. Elegilo otra vez en Ajustes." |
| Error, archivo de cookies inválido | "Ese archivo no sirve como cookies.txt: tiene que ser un .txt exportado en formato Netscape." |

### Pendientes técnicos

- **Cookies del navegador en Chrome/Edge nuevos**: Edge en esta PC da
  `Failed to decrypt with DPAPI` siempre (problema de yt-dlp, issue 10927). Firefox
  y Chrome no están instalados acá, así que el camino "con sesión del navegador"
  sigue sin probarse en vivo; solo con tests offline. La salida ya existe: el
  archivo de cookies de Ajustes (B2b), probado con archivos falsos.
- **Arrastre con mouse real**: se probó una vez con éxito (195,12 → 219,237). Las
  otras veces el clic cayó en otra ventana porque Windows no siempre deja poner la
  app adelante (`SetForegroundWindow` falla). Lo que sí está cubierto: pointer
  events sintéticos (límites, flechas, Shift, resize, pausa del conteo) y 23 tests.
- **La barra tapa el selector de calidad** mientras está visible en 1600×900,
  1355×721 y 1200×720 (decisión de Maki: nace abajo a la derecha y se arrastra).
  Si molesta, la alternativa es nacer más arriba o acortar el aviso.

## (i) Tandas 16–18/11/2026 — playlists, ajustes UI y archivos/cola (cerradas)

Hecho y verificado (detalle de commits en `DECISIONES.md` §3z y en el consolidado `Miauki YT.md`):

- **Playlists completas (16/11):** YouTube y YouTube Music con `list=`; análisis con `extract_flat`; pantalla con casillas + seleccionar todo + calidad global; encolado por video `[N/T]`; tope 100; catálogo de 19 causas de salteo con resumen agrupado (decisión de Maki: explicar el porqué). Suite 644.
- **Ajustes UI (17/11):** botones Cambiar/Abrir carpeta de "Guardar en" conectados; sincronización Ajustes↔Inicio; tope de playlist 500 en bloques automáticos de 200 con "Bloque X/Y"; refresh manual (recarga al instante); × para cerrar vista previa (se reactiva al re-analizar). Suite 653.
- **Archivos y cola (18/11):** el archivo descargado y el historial usan el título real (sin prefijos de bloque); botones globales Pausar/Reanudar/Cancelar todo + tacho rojo que vacía el historial (sin tocar archivos en disco); contador de activas en verde; fuente Normal / "Un poco más grande" (+10%); Acerca de +10% siempre con tope 1.17 combinado. Suite 666.

Pendientes vigentes (sin cambio): prueba manual Windows 10 limpio; prueba real TikTok/fotos de X; fotos/reels de Facebook (propuesta sin implementar); historial `core/history.py` sigue stub; `LICENCIAS.txt` dentro del paquete; `tools/build_exe.py` sale con exit 1 aunque genera el exe (cosmético).

## (j) Tanda 19/11/2026 — Instagram y URLs relajadas (cerradas)

Hecho y verificado (detalle de decisiones en `DECISIONES.md` §3aa y en el consolidado `Miauki YT.md`):

- **Historias de Instagram:** motor integrado (yt-dlp `InstagramStoryIE`); errores mapeados (pide sesión → guía a Ajustes; inalcanzable → eliminado); historias solo-imagen tratadas como imagen. Suite 693.
- **Cuentas públicas:** `instagram.com/usuario` → playlist de reels/publicaciones (tope 500, tandas de 200). ⚠️ En vivo NO funciona todavía: el extractor de perfiles del yt-dlp incluido está marcado no-funcional ("Unable to extract data") → pendiente actualizar el motor o cambiar de vía.
- **URLs relajadas:** se aceptan `www.` y dominios con ruta (antepone `https://`), se respeta `http://`; dominio sin ruta se rechaza. Mensaje de error actualizado en es/en.

Pendientes nuevos:
- Perfiles públicos de Instagram: probar tras "Actualizar motor" (o definir otra vía).
- Verificación en vivo de historias solo-imagen (requiere una sesión con una historia-imagen disponible).

## (k) Tanda 20/11/2026 — recorrido, cartel de traba, playlist y anti-bot (cerrada)

Hecho y verificado (detalle de decisiones en `DECISIONES.md` §3ab y en el consolidado `Miauki YT.md`):

- **Recorrido:** paso 8 "Refrescar" apuntando al botón de la columna derecha (es/en).
- **Cartel suave si la app se traba:** watchdog en el frontend (consulta cada 5 s, aviso a los 10 s sin respuesta, nunca con análisis o descargas activas), con Refrescar y Seguir esperando; se retira solo al volver el puente.
- **Inicio:** "Video" → "Previsualización" en la tarjeta de vista previa.
- **Playlist:** contador y botón MIAUK al doble, con escalones para ventanas bajas o angostas.
- **YouTube:** aviso anti-bot con mensaje propio y reintento (2 veces, 3 s); se recupera el error que yt-dlp ignoraba; playlist sin código de lista con mensaje claro. Suite 713, exe SHA-256 `04933A22…`.

Pendientes vigentes:

- Instalador (Inno Setup) y publicación en GitHub (código + exe en Release): siguientes pasos acordados, fuera de esta tanda.
- El aviso anti-bot depende de YouTube: si el bloqueo insiste, el mensaje pide esperar y reintentar; no se puede saltar sin sesión/cookies.
- El cartel "se traba" está probado con Node (mecanismo) y con el cableado de la interfaz; no se fuerza un cuelgue real del puente en la app.
- Siguen abiertos: prueba en Windows 10 limpio (Maki), TikTok/fotos de X con links reales, perfiles públicos de Instagram (motor), historial (`core/history.py` sigue stub), `LICENCIAS.txt` dentro del paquete y el exit 1 cosmético de `tools/build_exe.py`.

## (h) Tanda post-v1.0 — 07/09/11/2026 (cerrada)

Hecho y aprobado (ver `DECISIONES.md` §3y y el consolidado `Miauki YT.md`):

- **07/11:** banner nuevo "esto OK 2" sin logos de redes (`173bea4`); calidades hasta 8K con mp4/mkv separados y opción "Original" (`9e7f738`, `32245a1`, `6c70c60`); vías de imágenes Pinterest/Reddit/IG/FB/TikTok y mapeo de errores (`0b62118`); Acerca de con Instagram @tusrecursosdigitaless sin afiliación (`82adce3`); Paso C de cookies (ayuda desplegable, `4373151`); pulido visual neón (`5ab3cfb`).
- **08/11:** plan aprobado selector de calidades (grupo principal solo recomendadas + "Más opciones" sincronizado) y números 1/2/3 centrados ±1px (`c22107c`→`73b3ece`); X: posts con video (NSFW incluidos) ya no se descartan (`ac7621e`); calidades de X con peso real/duración/miniatura, vista previa más grande y datos del archivo en la Cola (`9a7a16b`).
- **09/11:** licencia GPL 3.0 + botón de donación (PayPal paypal.me/ezequielgottwald, alias makiezequiel.naranja, sin cripto; `3fe845d`); traducción al inglés completa (86 claves, automática según idioma de Windows; `821c28b`); Snapchat con vista previa (whitelist CDN) y peso real (`7cc6436`, `ec513fe`).

Cerrado en esta tanda:
- Textos de cookies de §(g): aprobados por Maki e implementados (Paso C). La tabla queda prácticamente toda aplicada.
- Números 1/2/3 centrados (desvío ≤1px), grosor 700.
- X con video: ya se descargan sin cookies.
- X con calidades completas y Cola con datos del archivo (sitio, formato, peso total, fecha/hora).
- Licencia GPL 3.0 + donación. Inglés completo. Snapchat: vista previa + peso real.

Pendientes vigentes:
- Prueba manual en Windows 10 limpio (Maki; `PRUEBA_EXE.md`). Instalador: NO creado (decisión).
- Douyin: fuera de alcance (requiere cookies frescas; decisión de Maki).
- Duración de Snapchat Spotlight: no disponible en la fuente (no inventar).
- Prueba real de TikTok/fotos de X (links de Maki). Historial (`core/history.py` sigue stub).
- Ruido de yt-dlp por stderr; `LICENCIAS.txt` dentro del paquete; actualizar runtime WebView2 (con OK).

## (i) Tanda 20/11 #2 — 20/11/2026 (cerrada)

Hecho y aprobado (ver `DECISIONES.md` §3ac):

- Calidad máxima de playlist híbrida (sondeo paralelo + decisión igual/mixto/fallback + salteados `calidad_insuficiente_playlist`).
- Límite de playlist 500 → 600.
- Música solo 320 kbps.

Pendientes vigentes:

- Instalador (Inno Setup) y publicación en GitHub (código + exe en Release).
- Prueba manual en Windows 10 limpio; TikTok/fotos de X; historial (`core/history.py` sigue stub).
- Prueba real del cartel forzando un cuelgue (queda para Maki).
- El equipo llegó al límite diario de modelos gratis; Maki va a resolver las API de OpenRouter.

- Corrección tanda 20/11 #2: playlist mixta ya no saltea por calidad (regla aprobada por Maki). Confirmado en vivo con playlist de YouTube Music (44 videos, 0 salteados, miniaturas OK). Exe SHA `e29b924c…`.

- Tanda 20/11 #2 (2ª parte): "Calidad Máxima" en playlist mixta + fix de cancelación en cola (postproceso y reintento anti-bot). Se reconstruyó el exe con el código al día: copiado a la raíz y a `dist` (idénticos), SHA `c7fa6695…`.

## Ajustes 21/11/2026 — cerrados

- Reanudar sin partes .part (reutiliza el parcial y limpia restos).
- Falsos eliminados: mapeo fino de causas + reintento de seguridad.
- Reintentar "Probar de nuevo" refresca el análisis.
- Historial: vistas previas reales + gatitos para archivos ausentes (3 imágenes).
- Aviso de privacidad en Ajustes y Acerca de.
- **Pendiente:** reconstruir el .exe cuando Maki lo pida (el actual sigue siendo el de `c7fa6695…`).

## Exe reconstruido - 21/11/2026

- El .exe quedó reconstruido con todo lo anterior (SHA `494009c2…`, raíz=dist). Queda pendiente el instalador Inno Setup y la publicación en GitHub.

## Cierre 21/11/2026 (fix cancelar todo)

- Cancelar todo funciona de nuevo (faltaba el método en el puente); los selectores de playlist piden MP4 compatible. Exe reconstruido SHA `e4886542…`. Sigue pendiente: instalador Inno Setup y publicación en GitHub.

---

## (22/11/2026) Auditoría extensiva — estado

- **Paso 1–2** (limpieza, YouTube): OK. Suite 735 passed + fallo de entorno preexistente (`test_motor::Reversa`).
- **Paso 5** Instagram Reel: OK (análisis + descarga mp4). **Paso 6** Facebook Reel: OK. **Paso 7** X video/imagen: OK; **X NSFW sin cookies: OK** (análisis + descarga). **Paso 8** Snapchat: OK (opción "Original", URL directa, sin cookies).
- **Playlists**: KPOP 100 entradas OK; 458 entradas OK (carga completa, 458); 8K 68 entradas OK (carga completa). Música siempre 320 kbps (verificado).
- **Fix 22/11**: sondeo de calidades de playlist con corte temprano por mezcla y presupuesto dinámico; si la muestra cubre ≥50% y todos coinciden → muestra la calidad uniforme real (8K/4K/2K) con advertencia. Commit `0f2ee49`.
- **Pendiente verificación en vivo**: la playlist 8K (PLT4S5qC9JaqOCmz7rbv_u47V5i8TCbNek) y la 458 quedaron mostrando "Calidad Máxima" porque YouTube bloqueó temporalmente la extracción individual (anti-bot por la ráfaga de pruebas). Reintentar el sondeo cuando YouTube se relaje; el código ya está preparado para mostrar 8K/4K/2K si todos coinciden.

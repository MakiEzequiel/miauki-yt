# Estado del backend — Miauki YT v1.0

Fecha: 20/10/2026. Mide el backend **tal como está** al cierre de la Fase 5 (Parte 0 y Parte B). No propone cambios: dice qué está completo, qué es un stub, qué cubren los tests y dónde está el riesgo.

## Cómo se midió

- Suite completa: `python -m unittest discover -s tests` → **408 tests, todos OK**.
- Cobertura: la suite corrida bajo `python -m trace --count --missing` (módulo `trace` de la biblioteca estándar, sin agregar dependencias). Se cuentan líneas ejecutables: las que corrieron y las marcadas `>>>>>>`.
- **Cobertura global del backend: 87 % (1784 de 2047 líneas ejecutables).**
- Límite de la medición: `app.py` corre en subprocesos en sus tests (`--version`, `--selftest`), así que no entra en el conteo; se valida aparte con `tests/test_app.py` (6 tests) y a mano con el `.exe`.

## Tabla por módulo

| Módulo | Qué hace | Estado | Tests | Cobertura | Qué NO cubre | Riesgo |
|---|---|---|---|---|---|---|
| `api.py` | puente JS↔Python: analizar, cola, ajustes, carpetas | Completo | `test_api` (24) | 87 % | ruta real de "Mostrar archivo" contra un archivo de la cola; validaciones de link vacío; el diálogo nativo de carpeta | Bajo |
| `app_info.py` | nombre, versión, autor, textos | Completo | indirecto | 100 % | nada | — |
| `events.py` | avisos de Python a la interfaz (progreso, cola) | Completo | sin tests propios | **43 %** | `emitir()` con ventana real (`run_js`); solo se ejerció en vivo (punto 3 de la Parte 0) | Medio: un fallo al avisar queda solo en el log |
| `paths.py` | rutas de datos, recursos y modo portable | Completo | `test_paths` (5) | 94 % | rama de `portable.flag` | Bajo |
| `core/analyzer.py` | análisis del link, calidades, música, subtítulos | Completo | `test_analyzer` (35) + `test_calidades` (15) | 95 % | errores de yt-dlp por sitio (edad, región, sesión), sitios exóticos | Medio: depende de la red y de yt-dlp |
| `core/assets_check.py` | lista negra de assets y manifiesto | Completo | `test_assets` (6) | 93 % | manifiesto corrupto | Bajo |
| `core/clipboard.py` | detectar links en el portapapeles (Win32 vía `ctypes`, sin dependencias) | Completo (Parte B, B1) | `test_clipboard` (11) | 89 % | portapapeles con formatos exóticos; error del sistema con la ventana cerrada | Bajo |
| `core/downloader.py` | descarga, pausa, reanudar, cancelar, subs | Completo | `test_downloader` (34) | 88 % | `_ruta_final` cuando `prepare_filename` falla; reintento con otro selector; pausa/cancelación contra yt-dlp real | Medio |
| `core/errors.py` | códigos y mensajes amables | Completo | `test_errors` (14) | 100 % | — | — |
| `core/ffmpeg_tools.py` | hash y verificación de ffmpeg | Completo | `test_ffmpeg_tools` (4) | 100 % | — | — |
| `core/formats.py` | tabla de calidades (Mejor/Equilibrada/Liviana) | Completo | `test_calidades` (15) | 100 % | — | — |
| `core/history.py` | historial de descargas: `historial.json` atómico, tope 500, tolerante a corrupción, miniatura validada | Completo (Fase 6, B1) | `test_history` (12) | s/d (no remedido) | nada | Bajo |
| `core/images.py` | imágenes de X (3 vías) + ruta de Facebook | Completo | `test_images` (25) | **74 %** | defensas anti-SSRF (IP privada, DNS, redirecciones, tamaño), fallos de cada vía de X, ruta de Facebook con un link real | Medio (seguridad) |
| `core/logger.py` | log con rotación | Completo | usado por toda la suite | 100 % | — | — |
| `core/queue_manager.py` | cola: agregar, pausar, reanudar, cancelar, borrar, limpiar | Completo | `test_queue_manager` (25) | 93 % | `cola_llena`, pausar un ítem "procesando", excepción inesperada del hilo | Bajo |
| `core/settings.py` | ajustes con escritura atómica | Completo | `test_settings` (14) | 94 % | error de disco al escribir | Bajo |
| `core/sites.py` | detectar sitio y normalizar el link | Completo | `test_sites` (20) | 93 % | dominios raros y variantes regionales | Bajo |
| `core/validacion.py` | borde: snapshot, rutas, nombres, carpetas | Completo | `test_validacion` (27) | 96 % | algunas ramas de rutas peligrosas | Bajo |
| `core/webview2.py` | detectar e instalar el runtime | Completo | `test_webview2` (7) | **71 %** | la descarga e instalación reales (habría que desinstalar WebView2), ramas de error | Bajo/Medio |
| `app.py` | arranque, selftest, instancia única, cierre | Completo | `test_app` (6, en subproceso) | no medida | el flujo con ventana real | Bajo |

Interfaz (no es backend, para contexto): `test_ui` (73), `test_textos` (2), `test_accesibilidad` (5).

## Los tres módulos que hay que mirar

1. **`events.py` (43 %)**: es el canal por el que la Cola se entera de los cambios. No tiene tests propios porque necesita una ventana real; en la Parte B se puede cubrir el armado del JSON sin ventana, que es donde podría romperse.
2. **`core/images.py` (74 %)**: la parte sin cubrir es justo la de seguridad (rechazo de IP privadas, redirecciones, tamaño). Es código defensivo y está escrito para fallar cerrado, pero no tiene tests que lo demuestren línea por línea.
3. **`core/history.py`**: sigue siendo un stub de una línea (es de su fase). `core/clipboard.py` **ya no**: en la Parte B quedó implementado de verdad (88 % de cobertura, 9 tests).

## Deuda conocida (además de la cobertura)

- **Facebook**: la ruta existe (`_via_facebook`) pero usa el extractor de yt-dlp, que **no soporta fotos**. Un link de foto devuelve un error genérico ("Ese sitio todavía no lo soportamos") en vez del mensaje específico que sí da el analizador. No hay código propio de Facebook. Propuesta y evidencia en `docs/PENDIENTES.md`.
- **`app.py`**: el flujo con ventana no se puede testear automatizado; se cubre con `--selftest`, los tests de subproceso y las pruebas en vivo.
- **Cola**: ya se persiste en `cola.json` (Fase 6, B3). Al arrancar, lo que quedó sin terminar aparece como "Interrumpida" y **no** se reanuda solo (decisión de Maki).
- **WebView2**: si el runtime falta y no hay internet, la app no abre; se avisa con un cuadro y queda en el log. El perfil de WebView2 es propio (`dir_datos()/webview2`) y el proceso se ata a un Job Object (A2): al cerrar Miauki no quedan `msedgewebview2.exe` suyos.

## Riesgo general

Bajo para el uso normal. Los dos riesgos reales son de red (yt-dlp cambia y algún sitio deja de andar) y de la instalación de WebView2 en una máquina sin runtime y sin internet. Ya no queda ningún módulo stub: `history` y la persistencia de la cola entraron en la Fase 6 y `diagnostico` es nuevo (A4).

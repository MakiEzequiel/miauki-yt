# Changelog

## [1.0.0] - 12/10/2026

### Fase 0
- Estructura inicial del proyecto.

### Fase 1 — Esqueleto técnico + prueba temprana de .exe
- `app_info.py` (datos únicos), `paths.py` (datos en %LOCALAPPDATA% o portable, interfaz externa/embebida), `core/logger.py` (logs con rotación), `core/ffmpeg_tools.py` (hash canónico del ffmpeg).
- Puente `api.py` (siempre `{ok, data|error}`, sin excepciones a la interfaz) y `events.py` (Python→JS con `run_js` + `json.dumps`, compatible con CSP estricta).
- `app.py`: `--selftest` (ffmpeg, yt-dlp, carpetas, WebView2, interfaz), `--version`, instancia única (mutex), ventana pywebview 1200×720 mín. 880×560 con motor `edgechromium`.
- `tools/build_exe.py`: verifica el ffmpeg y genera `dist/Miauki YT.exe` (PyInstaller onefile, 90,8 MB) con ícono `Miauki ico.ico` y metadatos.
- `requirements.txt` con versiones fijadas; 12 tests unittest en verde.

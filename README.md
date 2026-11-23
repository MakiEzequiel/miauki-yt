# Miauki YT 🐱

**Descargador de video, audio e imágenes para Windows.** Pegás un link y Miauki baja el contenido a tu carpeta: videos, shorts, playlists, canciones, reels, historias, fotos y más.

## Descargar

| Versión | Descarga | SHA-256 |
|---|---|---|
| **v1.0.0** | [Miauki.YT.v1.0.0.exe](https://github.com/MakiEzequiel/miauki-yt/releases/download/v1.0.0/Miauki.YT.v1.0.0.exe) | `2f976c8aa1c80d9677348d157734908eb9dbc034e0fcc84449d1d621c3bc9503` |
| **v1.0.0 (ZIP completo)** | [Miauki.YT.v1.0.0.-.Windows.zip](https://github.com/MakiEzequiel/miauki-yt/releases/download/v1.0.0/Miauki.YT.v1.0.0.-.Windows.zip) | `c47465d28c81f317a14e9f32db66e7106db88a981a3ddab9fe23d074240dd818` |

> Windows SmartScreen puede avisar al abrir el .exe por primera vez: es normal en programas sin certificado de firma. Elegí "Más información → Ejecutar de todas formas".

## Qué soporta

| Sitio | Contenido |
|---|---|
| **YouTube** | Videos, shorts, playlists, YouTube Music |
| **TikTok** | Videos, fotos (con sesión/cookies) |
| **Instagram** | Posts, reels, historias, highlights |
| **Facebook** | Videos, reels (fotos con sesión/cookies) |
| **X / Twitter** | Videos, fotos múltiples, NSFW (con cookies) |
| **Snapchat** | Spotlight e historias |
| **Google Imágenes** | Imágenes directas y links de share.google |
| **Otros** | Vimeo, Dailymotion, Reddit, Pinterest, SoundCloud y más (vía yt-dlp) |

## Características

- **Interfaz en español e inglés** (selector en Ajustes).
- **Cola de descargas** con pausar / reanudar / cancelar.
- **Cookies**: archivos `.txt` (Netscape) y `.json`, o elegí navegador (Chrome, Edge, Firefox, Brave, Chromium, Opera, Vivaldi) para contenido que pide sesión.
- **Calidades**: video hasta 4K/8K, música 320, imagen original (según el sitio).
- **Privacidad**: sin telemetría. Todo queda en tu PC.
- Ventana inicial 1420×840, redimensionable.

## Requisitos

- Windows 10/11 (con WebView2 Runtime; Miauki lo instala solo si falta).
- Para `--selftest` o correr desde código: Python 3.11+.

## Desde el código

```bash
pip install -r requirements.txt
python app.py            # abre la app
python app.py --selftest # verifica ffmpeg, yt-dlp, WebView2 e interfaz
python -m pytest         # suite de pruebas
```

## Documentación

- `docs/DECISIONES.md` — decisiones de diseño y arquitectura.
- `docs/PENDIENTES.md` — pendientes y limitaciones conocidas.
- `docs/DISTRIBUCION.md` — cómo se construye el .exe.

## Licencia

MIT — ver [LICENSE](LICENSE). Miauki integra yt-dlp, ffmpeg y otras librerías de terceros (detalle en `docs/LICENCIAS_TERCEROS.md`).
